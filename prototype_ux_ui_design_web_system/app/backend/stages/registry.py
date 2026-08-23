"""阶段卡注册表（stages 3-9 即插即用）。

StageCard = 网页工具的编排单元（SKILL.md 工具化映射）：
  阶段卡 = 一次有界 AI 调用；gate = 任务完成条件；decision_type = 界面确认控件形态。
卡文本快照在 stages/cards/（防 skill 升级导致 prompt 突变）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..workspace import WorkspaceManager

CARDS_DIR = Path(__file__).parent / "cards"


@dataclass(frozen=True)
class GateResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StageCard:
    stage: int
    name: str
    decision_type: str  # question_form | gallery | crit | none
    artifact_paths: list[str]
    artifact_map: dict[str, str]
    mock_dir: Path | None
    decision_data_path: str | None
    prompt_file: Path

    def build_prompt(self, ctx: dict[str, Any]) -> str:
        card_text = self.prompt_file.read_text(encoding="utf-8")
        return (
            f"你在执行「AI 设计工作台」九阶段工作流的阶段 {self.stage}（{self.name}）。\n"
            f"当前项目：{ctx['product_name']} · {ctx['project_name']}（{ctx['platform']}，画布 {ctx['canvas']}）。\n"
            f"工作目录即项目工作区；需求文档在 00-requirement.md。\n\n"
            f"阶段任务卡（严格按此执行）：\n---\n{card_text}\n---\n\n"
            f"产出要求：写 {'、'.join(self.artifact_paths)}"
            + (f"，决策数据写 {self.decision_data_path}（JSON，供界面表单消费）" if self.decision_data_path else "")
            + "。\n只写本阶段产物，不越阶段。产物内容用真实感样例数据，不用占位文案。"
        )

    def run_gate(self, ws: WorkspaceManager, project_dir: Path) -> GateResult:
        return GATES[self.stage](ws, project_dir)


# ---------- gate 实现 ----------

def _gate_stage01(ws: WorkspaceManager, project_dir: Path) -> GateResult:
    problems: list[str] = []
    memo = project_dir / "01-需求消化.md"
    if not memo.exists() or len(memo.read_text(encoding="utf-8").strip()) < 200:
        problems.append("01-需求消化.md 缺失或过短（<200 字）")
    qpath = project_dir / ".stage1-questions.json"
    if not qpath.exists():
        return GateResult(False, problems + [".stage1-questions.json 缺失（决策数据未产出）"])
    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        return GateResult(False, problems + [f".stage1-questions.json 不可解析：{e}"])
    blocking = data.get("blocking") or []
    if not blocking:
        problems.append("blocking 为空——阶段 1 至少要有一个阻塞性问题（A-x）")
    for q in blocking:
        if not q.get("id") or not q.get("text"):
            problems.append("存在缺 id/text 的阻塞问题")
            break
        rec = [o for o in q.get("options", []) if o.get("recommend")]
        if not rec:
            problems.append(f"{q.get('id')} 无推荐选项（零裸问）")
        for o in q.get("options", []):
            if not o.get("claim") or not o.get("consequence"):
                problems.append(f"{q.get('id')} 选项 {o.get('label')} 缺主张或后果（三件套不全）")
                break
    return GateResult(not problems, problems)


_MERMAID_FENCE = re.compile(r"```mermaid\r?\n(.*?)```", re.S)
_LABEL = re.compile(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}|\|[^|]*\|")
_IDENT = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*\b")
_ARROW = re.compile(r"--?>|-->|-\..*?\.->|-\.->|==>")
_SKIP_LINE = ("flowchart", "graph", "%%", "direction", "classDef", "class ", "style ", "end", "click")


def _mermaid_block_problems(block: str, idx: int) -> list[str]:
    """结构化检查：有边（无断链）、无孤儿节点（声明但无任何边连接）。"""
    edge_nodes: set[str] = set()
    def_nodes: set[str] = set()
    edge_count = 0
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith(_SKIP_LINE) or line.startswith("subgraph"):
            continue
        stripped = _LABEL.sub("", line)
        ids = _IDENT.findall(stripped)
        if not ids:
            continue
        if _ARROW.search(stripped) or "--" in stripped:
            if ids:
                edge_count += 1
                edge_nodes.update((ids[0], ids[-1]))
        elif re.search(r"\[|\(|\{", line):
            def_nodes.update(i for i in ids if i not in ("end",))
    if edge_count == 0:
        return [f"第 {idx} 个 mermaid 块无边（流程必须从触发走到出口，无断链）"]
    orphans = sorted(def_nodes - edge_nodes)
    return [f"第 {idx} 个 mermaid 块存在孤儿节点 {n}（声明了但无任何边连接）" for n in orphans]


def _gate_stage02(ws: WorkspaceManager, project_dir: Path) -> GateResult:
    fpath = project_dir / "02-流程草图.md"
    if not fpath.exists():
        return GateResult(False, ["02-流程草图.md 缺失"])
    text = fpath.read_text(encoding="utf-8")
    fences = _MERMAID_FENCE.findall(text)
    if not fences:
        return GateResult(False, ["未找到 mermaid 代码块（流程草图必须用 Mermaid，任务卡约定）"])
    problems: list[str] = []
    for i, block in enumerate(fences, 1):
        problems.extend(_mermaid_block_problems(block, i))
    return GateResult(not problems, problems)


GATES = {1: _gate_stage01, 2: _gate_stage02}


# ---------- 注册 ----------

def _card(stage: int, name: str, decision_type: str, artifacts: list[str], amap: dict[str, str] | None = None, decision_path: str | None = None) -> StageCard:
    return StageCard(
        stage=stage,
        name=name,
        decision_type=decision_type,
        artifact_paths=artifacts,
        artifact_map=amap or {a.split("/")[-1]: a for a in artifacts},
        mock_dir=CARDS_DIR / "mock" / f"stage{stage:02d}",
        decision_data_path=decision_path,
        prompt_file=CARDS_DIR / f"stage{stage:02d}.md",
    )


REGISTRY: dict[int, StageCard] = {
    1: _card(
        1, "需求消化", "question_form",
        ["01-需求消化.md"],
        {"01-需求消化.md": "01-需求消化.md", "stage1-questions.json": ".stage1-questions.json"},
        ".stage1-questions.json",
    ),
    2: _card(
        2, "流程草图", "confirm",  # M1: 确认走向（DecisionCard 简版确认）；M2 升级为流程审批+P2-x 表单
        ["02-流程草图.md"],
        None,
        None,
    ),
}

# 阶段 3-9 常量（阶段轨展示用；卡未注册=不可发起）
NINE_STAGES = ["需求消化", "流程草图", "屏幕与IA", "关键屏灰框", "视觉方向", "设计系统", "高保真", "交互与crit", "规格导出"]
