"""ClaudeRunner：`claude -p` headless 子进程（磁盘是唯一真相源）。

要点（来自 docs/architecture/2026-08-22-ai-prototype-tool-arch.md 的 spike 结论）：
- prompt 走 stdin（argv 放长 prompt 会撞限制）
- stream-json 逐行解析：assistant 的 tool_use(Write/Edit) → 产物增量；文本块 → 标题级步骤
- 单行可能 >64KB（result 行）——readline 上限 32MB，坏行容错跳过
- 超时按进程组杀（start_new_session + os.killpg）
- result.is_error=True 或非零退出码 → 抛异常（进 gate 重试语义）
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
from collections.abc import Awaitable, Callable
from pathlib import Path

from ..settings import Settings
from ..stages.registry import StageCard

StepCb = Callable[[str], Awaitable[None]]
ArtifactCb = Callable[[str], Awaitable[None]]

MAX_LINE = 32 * 1024 * 1024  # result 行可超 64KB（spike 实测）


class ClaudeRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def run(
        self,
        prompt: str,
        cwd: Path,
        card: StageCard,
        on_step: StepCb,
        on_artifact: ArtifactCb,
        canvas: tuple[int, int] | None = None,  # 画布硬约束已在 prompt 内；真实生成无需改写
        design_mode: str = "deliberate",        # 模式约束已在 prompt 内（引擎注入）
    ) -> None:
        cmd = [
            "claude", "-p",
            "--output-format", "stream-json",
            "--verbose",
            "--permission-mode", "acceptEdits",
        ]
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=True,  # 进程组：超时可整组杀
            limit=MAX_LINE,
        )
        assert proc.stdin and proc.stdout and proc.stderr

        async def pump() -> None:
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    return
                line = raw.decode("utf-8", "replace").strip()
                if not line or not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue  # 坏行容错
                await self._handle_event(ev, cwd, on_step, on_artifact)

        timeout = self.settings.task_timeout_s
        try:
            _, stderr_tail = await asyncio.wait_for(
                _communicate(proc, prompt.encode("utf-8"), pump),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            raise RuntimeError(f"任务超时（>{timeout}s），进程组已终止——失败无损，可重试") from None

        if proc.returncode != 0:
            raise RuntimeError(f"claude 退出码 {proc.returncode}：{(stderr_tail or b'')[-500:].decode('utf-8', 'replace')}")

    async def _handle_event(
        self,
        ev: dict,
        cwd: Path,
        on_step: StepCb,
        on_artifact: ArtifactCb,
    ) -> None:
        etype = ev.get("type")
        if etype == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                    fp = block.get("input", {}).get("file_path") or ""
                    if fp:
                        try:
                            rel = Path(fp).resolve().relative_to(cwd.resolve())
                        except ValueError:
                            rel = Path(fp)  # 工作区外（不展示为产物增量）
                        if str(rel) != ".":
                            await on_artifact(str(rel))
                elif block.get("type") == "text":
                    text = (block.get("text") or "").strip()
                    # 标题级步骤：取叙述文本的首行、截断（P2-2：不做日志流）
                    if text:
                        first = text.splitlines()[0][:80]
                        if not first.startswith("#"):
                            await on_step(first)
        elif etype == "result":
            if ev.get("is_error"):
                raise RuntimeError(f"claude 结果错误：{str(ev.get('result'))[:300]}")


async def _communicate(proc: asyncio.subprocess.Process, stdin_data: bytes, pump) -> tuple[bytes | None, bytes | None]:
    """并发：写 stdin、泵 stdout 事件、吸 stderr；返回 (None, stderr_tail)。"""
    stderr_tail = b""

    async def tap_stderr() -> None:
        nonlocal stderr_tail
        while True:
            line = await proc.stderr.readline()
            if not line:
                return
            stderr_tail = (stderr_tail + line)[-2000:]

    stdin_task = asyncio.create_task(_write_and_close(proc, stdin_data))
    pump_task = asyncio.create_task(pump())
    err_task = asyncio.create_task(tap_stderr())
    await asyncio.gather(stdin_task, pump_task, err_task)
    await proc.wait()
    return None, stderr_tail


async def _write_and_close(proc: asyncio.subprocess.Process, data: bytes) -> None:
    proc.stdin.write(data)
    await proc.stdin.drain()
    proc.stdin.close()
