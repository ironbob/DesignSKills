"""Runner：一次有界 AI 调用的执行器。

- MockRunner：即时产出罐头产物（开发/测试，不烧配额）；罐头按手机画布预制，
  复制时按项目画布参数化改写（.frame 宽高 / tokens.canvas / 文案里的画布字样）——
  三端预设都能在 mock 模式走通生成→gate→预览
- ClaudeRunner：真实生成（`claude -p --output-format stream-json` 子进程，cwd=项目工作区）；
  画布硬约束已写进 prompt，无需改写

接口约定（两实现一致）：
    await runner.run(prompt, cwd, card, on_step, on_artifact, canvas=(w,h)) -> None（异常=失败）
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Protocol

from ..stages.registry import StageCard

StepCb = Callable[[str], Awaitable[None]]            # 步骤标题（标题级，非日志流）
ArtifactCb = Callable[[str], Awaitable[None]]        # 新产物相对路径

Canvas = tuple[int, int]

_FRAME_RULE = re.compile(r"\.frame\s*\{[^}]*\}")


def _adapt_html_to_canvas(html: str, canvas: Canvas) -> str:
    """罐头 HTML → 项目画布：改写 .frame 规则的宽高声明与正文里的画布字样。"""
    w, h = canvas

    def _sub_rule(m: re.Match[str]) -> str:
        rule = re.sub(r"(?<![a-zA-Z-])width:\d+px", f"width:{w}px", m.group(0))
        return re.sub(r"(?<![a-zA-Z-])height:\d+px", f"height:{h}px", rule)

    html = _FRAME_RULE.sub(_sub_rule, html)
    return html.replace("390×844", f"{w}×{h}").replace("390x844", f"{w}x{h}")


def _adapt_json_to_canvas(text: str, canvas: Canvas) -> str:
    """罐头 JSON（06-tokens.json）→ 项目画布：canvas.width/height 与规则文案里的画布字样同步。"""
    w, h = canvas
    try:
        data = json.loads(text)
    except ValueError:
        return text.replace("390×844", f"{w}×{h}")
    cv = data.get("canvas") if isinstance(data, dict) else None
    if isinstance(cv, dict) and "width" in cv and "height" in cv:
        cv["width"], cv["height"] = canvas
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").replace("390×844", f"{w}×{h}")


class Runner(Protocol):
    async def run(
        self,
        prompt: str,
        cwd: Path,
        card: StageCard,
        on_step: StepCb,
        on_artifact: ArtifactCb,
        canvas: Canvas | None = None,
    ) -> None: ...


class MockRunner:
    """即时罐头：复制 card.mock_dir 下的预置产物到工作区（按项目画布改写），逐步骤发事件。"""

    def __init__(self, delay_s: float = 0.8) -> None:
        self.delay_s = delay_s

    async def run(
        self,
        prompt: str,
        cwd: Path,
        card: StageCard,
        on_step: StepCb,
        on_artifact: ArtifactCb,
        canvas: Canvas | None = None,
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
            if src.is_dir():  # 目录产物（04-wireframes/ 等）：整树复制，逐文件发增量
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, dest, dirs_exist_ok=True)
                for f in sorted(dest.rglob("*")):
                    if f.is_file():
                        if canvas is not None:
                            self._adapt_file(f, canvas)
                        await on_artifact(str(f.relative_to(cwd)))
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                if canvas is not None:
                    self._adapt_file(dest, canvas)
                await on_artifact(str(dest.relative_to(cwd)))
        await asyncio.sleep(self.delay_s)
        await on_step(f"{card.name} 产物生成完毕")

    @staticmethod
    def _adapt_file(path: Path, canvas: Canvas) -> None:
        """罐头是手机 390×844 预制；非该画布的项目按目标画布改写（幂等，不影响既有项目数据）。"""
        if canvas == (390, 844) or path.suffix not in (".html", ".md", ".json"):
            return
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return
        adapted = _adapt_json_to_canvas(text, canvas) if path.suffix == ".json" else _adapt_html_to_canvas(text, canvas)
        if adapted != text:
            path.write_text(adapted, encoding="utf-8")
