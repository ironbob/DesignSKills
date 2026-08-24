"""workspace 路径安全与布局测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.workspace import WorkspaceError, WorkspaceManager


@pytest.fixture()
def ws(tmp_path: Path) -> WorkspaceManager:
    return WorkspaceManager(tmp_path)


def _mk_project(ws: WorkspaceManager, tmp_path: Path, pid: int = 1) -> Path:
    ws.create_product(9, "产品A", "req.md", "# 需求\n内容")
    return ws.create_project(pid, 9, "# 需求\n内容", "req.md")


def test_create_project_layout(ws: WorkspaceManager, tmp_path: Path):
    wdir = _mk_project(ws, tmp_path)
    assert (wdir / "00-requirement.md").read_text(encoding="utf-8").startswith("<!--")
    for d in ("04-wireframes", "05-style-tiles", "07-hifi", "snapshots"):
        assert (wdir / d).is_dir()


def test_resolve_rejects_escape(ws: WorkspaceManager, tmp_path: Path):
    wdir = _mk_project(ws, tmp_path)
    with pytest.raises(WorkspaceError):
        ws.resolve(wdir, "../9/requirement.md")
    with pytest.raises(WorkspaceError):
        ws.resolve(wdir, "04-wireframes/../../9/requirement.md")
    with pytest.raises(WorkspaceError):
        ws.resolve(wdir, "/etc/passwd")


def test_resolve_rejects_missing(ws: WorkspaceManager, tmp_path: Path):
    wdir = _mk_project(ws, tmp_path)
    with pytest.raises(WorkspaceError):
        ws.resolve(wdir, "01-需求消化.md")  # 尚未生成


def test_resolve_accepts_nested(ws: WorkspaceManager, tmp_path: Path):
    wdir = _mk_project(ws, tmp_path)
    target = wdir / "04-wireframes" / "s1.html"
    target.parent.mkdir(exist_ok=True)
    target.write_text("<html></html>", encoding="utf-8")
    assert ws.resolve(wdir, "04-wireframes/s1.html") == target


def test_snapshot_copies_without_snapshots_dir(ws: WorkspaceManager, tmp_path: Path):
    wdir = _mk_project(ws, tmp_path)
    ws.write_text(wdir, "01-需求消化.md", "# memo")
    dest = ws.snapshot(wdir, seq=1, stage=1)
    assert (dest / "01-需求消化.md").exists()
    assert not (dest / "snapshots").exists()  # 快照不递归自身
