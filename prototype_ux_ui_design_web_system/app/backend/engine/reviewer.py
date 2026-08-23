"""L2 评审器（Generator–Critic 的 Critic 侧）。

- MockReviewer：即时全绿罐头（开发/测试；findings 可注入，供打回场景测试）
- ClaudeReviewer：`claude -p` 独立会话——fresh context，只读产物，stdout 输出 findings JSON

关键设计（review-conventions.md）：
- 评审器只产出 findings（🔴/🟡 + 证据），**verdict 由引擎数出**（🔴=0），评审器无裁量权
- 评审 prompt 只含判据卡 + 评审公约 + 产物清单，不含生成任务卡与生成过程（防错误相关）
- 判据覆盖完整性在解析侧强校验：covered + not_applicable 缺项 = 评审不可信，等同 redo
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
from pathlib import Path
from typing import Any, Protocol

from ..stages.registry import StageCard
from ..workspace import WorkspaceManager

MAX_LINE = 32 * 1024 * 1024


class ReviewError(Exception):
    """评审失败（进程/解析/覆盖不完整）。引擎按打回语义处理或转人工。"""


def parse_review_payload(raw: str, card: StageCard) -> dict[str, Any]:
    """解析评审输出 → findings dict；强校验结构。抛 ReviewError。"""
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ReviewError("评审输出中未找到 JSON 对象")
    try:
        data = json.loads(m.group(0))
    except ValueError as e:
        raise ReviewError(f"评审输出 JSON 不可解析：{e}") from e

    findings = data.get("findings")
    if not isinstance(findings, list):
        raise ReviewError("findings 缺失或非数组")
    for f in findings:
        if not isinstance(f, dict) or f.get("severity") not in ("red", "yellow") or not f.get("criterion"):
            raise ReviewError(f"finding 结构非法：{str(f)[:120]}")

    covered = {str(c) for c in data.get("covered", []) if c}
    na = {str(n.get("criterion")) for n in data.get("not_applicable", []) if isinstance(n, dict) and n.get("criterion")}
    missing = card.criterion_ids - covered - na
    if missing:
        raise ReviewError(f"判据覆盖不完整（沉默即违规，等同打回）：{sorted(missing)}")
    return data


class Reviewer(Protocol):
    async def review(self, card: StageCard, project_dir: Path, ws: WorkspaceManager) -> dict[str, Any]: ...


class MockReviewer:
    """罐头评审：默认全绿；findings 可注入（测试打回/重试链）。"""

    def __init__(self, findings: list[dict[str, Any]] | None = None) -> None:
        self.findings = findings or []

    async def review(self, card: StageCard, project_dir: Path, ws: WorkspaceManager) -> dict[str, Any]:
        return {
            "stage": card.stage,
            "findings": self.findings,
            "covered": sorted(card.criterion_ids),
            "not_applicable": [],
        }


class ClaudeReviewer:
    """`claude -p` headless 评审会话：只读产物，JSON 到 stdout，不写任何文件。"""

    def __init__(self, settings: Any) -> None:
        self.settings = settings
        self._conventions = (Path(__file__).resolve().parents[1] / "stages" / "cards" / "review-conventions.md").read_text(encoding="utf-8")

    def build_prompt(self, card: StageCard, artifacts: list[str]) -> str:
        rubric = card.rubric_file.read_text(encoding="utf-8")
        # 注意：公约/判据卡全文含字面 %（如「100%」），禁止对拼接串做 %-formatting
        return (
            "你是独立设计评审器（L2）。只读产物、只出 findings，禁止改任何文件，禁止打分。\n\n"
            f"## 评审公约（硬约束）\n---\n{self._conventions}\n---\n\n"
            f"## 阶段 {card.stage}（{card.name}）判据卡\n---\n{rubric}\n---\n\n"
            f"## 待审产物（工作目录内相对路径）\n{'、'.join(artifacts)}\n\n"
            "逐条判据判定（命中/未命中/不适用+理由），然后**只输出一个 JSON 对象**（无其他文字）：\n"
            f'{{"stage": {card.stage}, "findings": [{{"id","criterion","severity":"red|yellow","evidence","suggestion"}}], '
            f'"covered": ["R{card.stage}-x", ...], "not_applicable": [{{"criterion","reason"}}]}}'
        )

    async def review(self, card: StageCard, project_dir: Path, ws: WorkspaceManager) -> dict[str, Any]:
        artifacts = [p for p in card.artifact_paths if (project_dir / p).exists()]
        if not artifacts:
            raise ReviewError("产物文件均不存在，无可审内容")
        prompt = self.build_prompt(card, artifacts)
        raw = await self._run_claude(prompt, project_dir)
        return parse_review_payload(raw, card)

    async def _run_claude(self, prompt: str, cwd: Path) -> str:
        cmd = ["claude", "-p", "--output-format", "stream-json", "--verbose"]
        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=str(cwd), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=env, start_new_session=True, limit=MAX_LINE,
        )
        assert proc.stdin and proc.stdout

        async def pump() -> str:
            result_text = ""
            while True:
                raw = await proc.stdout.readline()
                if not raw:
                    return result_text
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("{"):
                    continue
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                if ev.get("type") == "result":
                    if ev.get("is_error"):
                        raise ReviewError(f"评审会话错误：{str(ev.get('result'))[:300]}")
                    result_text = str(ev.get("result") or "")

        async def write_stdin() -> None:
            proc.stdin.write(prompt.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

        timeout = self.settings.task_timeout_s
        try:
            results = await asyncio.wait_for(
                asyncio.gather(write_stdin(), pump()), timeout=timeout
            )
        except asyncio.TimeoutError:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            raise ReviewError(f"评审超时（>{timeout}s），进程组已终止") from None
        if proc.returncode != 0:
            raise ReviewError(f"claude 评审退出码 {proc.returncode}")
        if not results[1]:
            raise ReviewError("评审无 result 输出")
        return results[1]
