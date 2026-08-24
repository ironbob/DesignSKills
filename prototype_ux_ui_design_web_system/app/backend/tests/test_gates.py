"""stage02 mermaid gate 的通过/失败路径（card02 注册已完成，e2e 已走通成功路径）。"""

from __future__ import annotations

from pathlib import Path

from backend.stages.registry import REGISTRY, _gate_stage02
from backend.workspace import WorkspaceManager


def _ws_with_flow(tmp_path: Path, content: str) -> Path:
    ws = WorkspaceManager(tmp_path)
    ws.create_product(1, "P", "req.md", "# 需求")
    wdir = ws.create_project(1, 1, "# 需求", "req.md")
    (wdir / "02-流程草图.md").write_text(content, encoding="utf-8")
    return wdir


def _wrap(blocks: list[str]) -> str:
    return "# 02 · 流程草图\n" + "".join(f"\n```mermaid\n{b}\n```\n" for b in blocks)


def test_gate_passes_connected_graph(tmp_path: Path):
    wdir = _ws_with_flow(
        tmp_path,
        _wrap(["flowchart TD\n    A([触发]) --> B[停留]\n    B --> C{判断}\n    C -.支线.-> D[终点]\n    C -->|通过| D"]),
    )
    result = _gate_stage02(None, wdir)  # type: ignore[arg-type]
    assert result.ok, result.problems


def test_gate_passes_subgraph_and_self_loop(tmp_path: Path):
    wdir = _ws_with_flow(
        tmp_path,
        _wrap(["flowchart TD\n    A --> B\n    subgraph HEART[状态机]\n        B[屏] -->|循环| B\n    end\n    B --> C([出口])"]),
    )
    result = _gate_stage02(None, wdir)  # type: ignore[arg-type]
    assert result.ok, result.problems


def test_gate_rejects_missing_file(tmp_path: Path):
    ws = WorkspaceManager(tmp_path)
    ws.create_product(1, "P", "req.md", "# 需求")
    wdir = ws.create_project(1, 1, "# 需求", "req.md")
    result = _gate_stage02(None, wdir)  # type: ignore[arg-type]
    assert not result.ok


def test_gate_rejects_no_mermaid(tmp_path: Path):
    wdir = _ws_with_flow(tmp_path, "# 02\n只有文字没有图\n")
    result = _gate_stage02(None, wdir)  # type: ignore[arg-type]
    assert not result.ok
    assert "mermaid" in result.problems[0]


def test_gate_rejects_orphan_node(tmp_path: Path):
    wdir = _ws_with_flow(tmp_path, _wrap(["flowchart TD\n    A --> B\n    Z[孤儿节点]"]))
    result = _gate_stage02(None, wdir)  # type: ignore[arg-type]
    assert not result.ok
    assert any("孤儿" in p for p in result.problems)


def test_gate_rejects_edgeless_block(tmp_path: Path):
    wdir = _ws_with_flow(tmp_path, _wrap(["flowchart TD\n    A[只有节点没有边]"]))
    result = _gate_stage02(None, wdir)  # type: ignore[arg-type]
    assert not result.ok


def test_mock_stage02_artifact_passes_gate(tmp_path: Path):
    """MockRunner 的罐头产物必须过自己的 gate（罐头与 gate 永不脱节）。"""
    ws = WorkspaceManager(tmp_path)
    ws.create_product(1, "P", "req.md", "# 需求")
    wdir = ws.create_project(1, 1, "# 需求", "req.md")
    card = REGISTRY[2]
    for src in card.mock_dir.iterdir():  # type: ignore[union-attr]
        if not src.name.startswith("."):
            (wdir / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    assert card.run_gate(ws, wdir).ok
