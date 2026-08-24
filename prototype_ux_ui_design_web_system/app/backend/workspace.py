"""工作区管理（磁盘是唯一真相源）。

布局：
  <data_dir>/workbench.db
  <data_dir>/products/<product_id>/requirement.md          产品级共享需求文档（母本）
  <data_dir>/products/<product_id>/projects/<project_id>/  项目工作区 = skill 布局
      00-requirement.md（拷贝，文档替换时刷新）
      01-需求消化.md … 09-spec.md / 04-wireframes/ … snapshots/
      revisions/<revision_id>/                              增量变更工作区（继承基线快照，独立执行）

路径安全：一切外部传入的相对路径必须落在项目目录内（拒绝绝对路径与 .. 逃逸）。
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

# skill 工作区契约的编号产物（创建项目时预置目录说明，文件由 AI 任务产出）
STAGE_DIRS = ("04-wireframes", "05-style-tiles", "07-hifi", "snapshots")

_SAFE_NAME = re.compile(r"^[\w一-鿿.#-]+$")


class WorkspaceError(Exception):
    """工作区路径非法或产物不存在。"""


class WorkspaceManager:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.products_root = data_dir / "products"

    # ---------- 目录 ----------
    def product_dir(self, product_id: int) -> Path:
        return self.products_root / str(product_id)

    def project_dir(self, project_id: int, product_id: int | None = None) -> Path:
        if product_id is not None:
            return self.product_dir(product_id) / "projects" / str(project_id)
        # 仅按项目定位（遍历一层），数据量小可接受
        for pdir in self.products_root.glob("*/projects"):
            cand = pdir / str(project_id)
            if cand.is_dir():
                return cand
        raise WorkspaceError(f"project workspace not found: {project_id}")

    # ---------- 创建 ----------
    def create_product(self, product_id: int, name: str, requirement_doc_name: str, requirement_text: str) -> Path:
        pdir = self.product_dir(product_id)
        (pdir / "projects").mkdir(parents=True, exist_ok=True)
        self._write_doc_master(pdir, requirement_doc_name, requirement_text)
        return pdir

    def _write_doc_master(self, product_dir: Path, doc_name: str, text: str) -> None:
        safe = _SAFE_NAME.match(doc_name) and ".." not in doc_name
        master = product_dir / "requirement.md"
        header = f"# 需求文档 · {doc_name if safe else 'requirements'}\n\n"
        master.write_text(header + text, encoding="utf-8")

    def create_project(self, project_id: int, product_id: int, requirement_text: str, doc_name: str) -> Path:
        wdir = self.project_dir(project_id, product_id)
        wdir.mkdir(parents=True, exist_ok=True)
        for d in STAGE_DIRS:
            (wdir / d).mkdir(exist_ok=True)
        (wdir / "snapshots" / ".gitkeep").write_text("", encoding="utf-8")
        # 00-requirement.md = 产品文档的项目内拷贝（AI 任务 cwd=项目工作区）
        self.refresh_requirement_copy(project_id, product_id, requirement_text, doc_name)
        return wdir

    def refresh_requirement_copy(self, project_id: int, product_id: int, requirement_text: str, doc_name: str) -> None:
        wdir = self.project_dir(project_id, product_id)
        header = f"<!-- 来源：产品级需求文档 {doc_name}（替换文档时自动刷新） -->\n\n"
        (wdir / "00-requirement.md").write_text(header + requirement_text, encoding="utf-8")

    # ---------- 产物访问（路径安全） ----------
    def resolve(self, project_dir: Path, rel_path: str) -> Path:
        if not rel_path or rel_path.startswith(("/", "\\")) or "\x00" in rel_path:
            raise WorkspaceError(f"illegal path: {rel_path!r}")
        cand = (project_dir / rel_path).resolve()
        root = project_dir.resolve()
        if cand != root and root not in cand.parents:
            raise WorkspaceError(f"path escapes workspace: {rel_path!r}")
        if not cand.exists():
            raise WorkspaceError(f"artifact not found: {rel_path!r}")
        return cand

    def read_text(self, project_dir: Path, rel_path: str) -> str:
        return self.resolve(project_dir, rel_path).read_text(encoding="utf-8")

    def write_text(self, project_dir: Path, rel_path: str, text: str) -> Path:
        target = project_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.parent.resolve() != project_dir.resolve() and project_dir.resolve() not in target.parent.resolve().parents:
            raise WorkspaceError(f"path escapes workspace: {rel_path!r}")
        target.write_text(text, encoding="utf-8")
        return target

    # ---------- 快照（R6：目录拷贝） ----------
    def snapshot(self, project_dir: Path, seq: int, stage: int, reason: str = "") -> Path:
        dest = project_dir / "snapshots" / f"#{seq}"
        if dest.exists():
            shutil.rmtree(dest)
        # revision 工作区内的快照需排除同级 revisions 目录（revision 不嵌套）
        ignore = ["snapshots", "revisions"] if (project_dir / "revisions").is_dir() else ["snapshots"]
        shutil.copytree(project_dir, dest, ignore=shutil.ignore_patterns(*ignore))
        meta = f"seq={seq}\nstage={stage}\n" + (f"reason={reason}\n" if reason else "")
        (dest / ".snapshot-meta.txt").write_text(meta, encoding="utf-8")
        return dest

    # ---------- 增量变更工作区（revision：继承基线快照，独立执行） ----------
    def revision_dir(self, project_id: int, revision_id: int, product_id: int | None = None) -> Path:
        return self.project_dir(project_id, product_id) / "revisions" / str(revision_id)

    def create_revision_workspace(
        self,
        project_id: int,
        product_id: int,
        revision_id: int,
        base_snapshot_dir: Path,
        change_request: dict,
    ) -> Path:
        """基线快照整树副本 → revisions/<id>/；原项目与快照目录不写入。

        继承物：基线的全部阶段产物（01 台账 / 02 流程 / 03 IA / 04-08 / 09-spec / 06-tokens / 07-hifi），
        增量阶段只覆盖受影响产物。00-change-request.md 记录新需求与基线出处。
        """
        rdir = self.revision_dir(project_id, revision_id, product_id)
        if rdir.exists():
            raise WorkspaceError(f"revision workspace already exists: {revision_id}")
        shutil.copytree(base_snapshot_dir, rdir, ignore=shutil.ignore_patterns("snapshots", ".snapshot-meta.txt"))
        (rdir / "snapshots").mkdir(exist_ok=True)
        (rdir / "snapshots" / ".gitkeep").write_text("", encoding="utf-8")
        header = (
            f"<!-- 增量变更请求 R{change_request.get('seq', revision_id)} · 基线：快照 #{change_request.get('base_seq', '?')}"
            f"（id={change_request.get('base_snapshot_id', '?')}） · 本工作区继承基线全部产物，只重做受影响阶段 -->\n\n"
        )
        (rdir / "00-change-request.md").write_text(
            header + f"# {change_request.get('title', '设计变更')}\n\n"
            + (f"来源文件：{change_request['doc_name']}\n\n" if change_request.get("doc_name") else "")
            + (f"变更说明：{change_request['reason']}\n\n" if change_request.get("reason") else "")
            + change_request.get("requirement_text", ""),
            encoding="utf-8",
        )
        return rdir

    def snapshot_files(self, project_dir: Path, seq: int) -> list[dict]:
        """快照内文件清单（供查看/恢复前核对；快照本身只读）。"""
        sdir = project_dir / "snapshots" / f"#{seq}"
        if not sdir.is_dir():
            raise WorkspaceError(f"snapshot not found: #{seq}")
        items: list[dict] = []
        for p in sorted(sdir.rglob("*")):
            if not p.is_file() or p.name.startswith("."):
                continue
            if p.suffix in (".md", ".html", ".json"):
                items.append({"path": str(p.relative_to(sdir)), "kind": p.suffix.lstrip("."), "mtime": int(p.stat().st_mtime)})
        return items

    def restore_snapshot(self, project_dir: Path, seq: int, safety_seq: int) -> None:
        """项目工作区还原为快照 #seq：先以 safety_seq 保全当前状态为新快照，再整树替换（快照本体不动）。

        删除当前阶段产物后拷入快照内容（00-requirement.md 一并还原，产品级母本不受影响；
        revisions/ 与 snapshots/ 保留——增量工作区独立于回退）。
        """
        sdir = project_dir / "snapshots" / f"#{seq}"
        if not sdir.is_dir():
            raise WorkspaceError(f"snapshot not found: #{seq}")
        self.snapshot(project_dir, safety_seq, 0, reason="回退前保全（自动）")
        for p in list(project_dir.iterdir()):
            if p.name == "snapshots" or p.name == "revisions":
                continue
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        for p in sdir.iterdir():
            if p.name.startswith(".") or p.name == "snapshots":
                continue
            dest = project_dir / p.name
            if p.is_dir():
                shutil.copytree(p, dest)
            else:
                shutil.copy2(p, dest)
