"""Runner：一次有界 AI 调用的执行器。

- MockRunner：即时产出罐头产物（开发/测试，不烧配额）
- ClaudeRunner：M1-6 接入（`claude -p --output-format stream-json` 子进程，cwd=项目工作区）

接口约定（两实现一致）：
    await runner.run(prompt, cwd, card, on_step, on_artifact) -> None（异常=失败，message 即原因）
"""

from __future__ import annotations

import asyncio
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

from ..stages.registry import StageCard

StepCb = Callable[[str], Awaitable[None]]            # 步骤标题（标题级，非日志流）
ArtifactCb = Callable[[str], Awaitable[None]]        # 新产物相对路径


class Runner(Protocol):
    async def run(
        self,
        prompt: str,
        cwd: Path,
        card: StageCard,
        on_step: StepCb,
        on_artifact: ArtifactCb,
    ) -> None: ...


class MockRunner:
    """即时罐头：复制 card.mock_dir 下的预置产物到工作区，逐步骤发事件。"""

    def __init__(self, delay_s: float = 0.8) -> None:
        self.delay_s = delay_s

    async def run(
        self,
        prompt: str,
        cwd: Path,
        card: StageCard,
        on_step: StepCb,
        on_artifact: ArtifactCb,
    ) -> None:
        mock_dir = card.mock_dir
        if mock_dir is None:
            raise RuntimeError(f"阶段 {card.stage} 无 mock 产物（card 未定义 mock_dir）")
        await on_step(f"读取 00-requirement.md · 构建 {card.name} 任务上下文")
        await asyncio.sleep(self.delay_s)
        await on_step(f"正在生成 {card.name} 产物")
        for src in sorted(mock_dir.iterdir()):
            if src.name.startswith("."):
                continue
            await asyncio.sleep(self.delay_s * 0.6)
            dest = cwd / card.artifact_map.get(src.name, src.name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            await on_artifact(str(dest.relative_to(cwd)))
        await asyncio.sleep(self.delay_s)
        await on_step(f"{card.name} 产物生成完毕")
