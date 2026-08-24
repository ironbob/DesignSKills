"""增量设计变更 service：revision 生命周期（创建→影响分析→确认范围→增量执行→合并）。

不变量：
- 原项目工作区与全部历史快照（snapshots/#N）只读——增量产物只写 revisions/<id>/；
- merge 是唯一把 revision 产物带回项目工作区的路径，且带回前先落项目快照（历史不丢）；
- 页面级模型（pages 表）在确认范围时登记，合并时收口——产物与决策都能按页面范围追溯。
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..db import Database, parse_json_or
from ..workspace import WorkspaceManager
from .advance import AdvanceError, AnswerIn, DefaultIn, validate_stage_decision
from .impact import load_impact, plan_from_impact, screen_rows

REV_ACTIVE_STATES = ("analyzing", "impact_ready", "running", "completed")

# merge 拷回项目时排除的 revision 专属文件（revisions/ 与 snapshots/ 由调用方处理）
_REVISION_ONLY_FILES = {"00-change-request.md", "00-impact.md", "00-impact.json"}


class RevisionError(Exception):
    """revision 前置条件不满足（状态不对/影响分析缺失/契约不全）。"""


@dataclass
class RevisionResult:
    ok: bool = True
    status: str = ""
    next_stage: int | None = None
    snapshot_seq: int | None = None
    version: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


# ---------- 创建 ----------

def create_revision(
    db: Database, ws: WorkspaceManager, project_id: int,
    title: str, requirement_text: str, doc_name: str | None, reason: str,
    base_snapshot_id: int | None = None,
) -> dict[str, Any]:
    """创建 revision：校验基线快照 → 建独立工作区（整树继承基线）→ 落库 → 注册基线页面。

    创建后只做影响分析（阶段 0 由路由入队），不立即重跑任何设计阶段。
    """
    project = db.one("SELECT p.*, pr.name AS product_name FROM projects p JOIN products pr ON pr.id=p.product_id WHERE p.id=?", (project_id,))
    if project is None:
        raise RevisionError(f"项目不存在：{project_id}")
    snaps = db.query("SELECT id, seq, stage FROM snapshots WHERE project_id=? ORDER BY seq", (project_id,))
    if not snaps:
        raise RevisionError("项目尚无已确认快照（至少完成一个阶段决策后才能创建设计变更）")
    base = None
    if base_snapshot_id is not None:
        base = next((s for s in snaps if s["id"] == base_snapshot_id), None)
        if base is None:
            raise RevisionError(f"基线快照不存在或不属于该项目：{base_snapshot_id}")
    else:
        base = snaps[-1]  # 默认 = 最新已确认快照（已完成项目即最终交付快照）
    project_dir = ws.project_dir(project_id, project["product_id"])
    base_dir = project_dir / "snapshots" / f"#{base['seq']}"
    if not base_dir.is_dir():
        raise RevisionError(f"基线快照目录缺失：#{base['seq']}（磁盘是唯一真相源，先核对工作区）")

    seq = len(db.query("SELECT id FROM revisions WHERE project_id=?", (project_id,))) + 1
    rid = db.execute(
        "INSERT INTO revisions (project_id, seq, title, requirement_text, doc_name, reason, base_snapshot_id, status, stage_status) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (project_id, seq, title, requirement_text, doc_name, reason, base["id"], "analyzing", '{"0":"ready"}'),
    )
    ws.create_revision_workspace(project_id, project["product_id"], rid, base_dir, {
        "seq": seq, "title": title, "reason": reason, "doc_name": doc_name,
        "requirement_text": requirement_text, "base_seq": base["seq"], "base_snapshot_id": base["id"],
    })
    _register_baseline_pages(db, project_id, project_dir)
    revision = db.one("SELECT * FROM revisions WHERE id=?", (rid,))
    revision["base_seq"] = base["seq"]
    return revision


def _register_baseline_pages(db: Database, project_id: int, project_dir: Path) -> None:
    """基线页面登记（幂等）：03 盘点表 → pages 表（origin/last NULL=初始项目）。"""
    for row in screen_rows(project_dir):
        db.execute(
            "INSERT OR IGNORE INTO pages (project_id, page_id, name, level, lifecycle, status) "
            "VALUES (?,?,?,?, 'initial', 'live')",
            (project_id, row["page_id"], row["name"], row["name"]),
        )


# ---------- 确认范围 ----------

def confirm_scope(db: Database, ws: WorkspaceManager, project_id: int, revision_id: int, reason: str = "") -> RevisionResult:
    """确认影响分析：锁定执行计划（确定性 planner）、登记页面级变更、解锁受影响阶段。

    stage 图重置为 {0: done, s1: ready, s2: ready…}——revision 独立状态机，
    不受项目主流程"已完成阶段不可再次执行"限制。
    """
    revision = _revision(db, project_id, revision_id)
    if revision["status"] != "impact_ready":
        raise RevisionError(f"revision 不在待确认范围状态（当前：{revision['status']}）")
    project = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    rdir = ws.revision_dir(project_id, revision_id, project["product_id"])
    analysis = load_impact(rdir)
    if analysis is None:
        raise RevisionError("00-impact.json 缺失或不可解析（先完成影响分析任务）")
    plan = plan_from_impact(analysis)
    if not plan["stages_to_rerun"]:
        raise RevisionError("执行计划为空（任何变更至少重跑阶段 9）")

    impact = {"analysis": analysis, "plan": plan, "confirmed_reason": reason or None}
    stage_map = {"0": "done", **{str(s): "ready" for s in plan["stages_to_rerun"]}}
    db.execute(
        "UPDATE revisions SET status='running', change_levels=?, impact=?, stage_status=?, updated_at=datetime('now','localtime') WHERE id=?",
        (json.dumps(plan["change_levels"], ensure_ascii=False),
         json.dumps(impact, ensure_ascii=False), json.dumps(stage_map), revision_id),
    )
    _apply_page_changes(db, project_id, revision_id, analysis, plan)

    events = [
        {"type": "revision_state", "project_id": project_id, "revision_id": revision_id,
         "status": "running", "detail": f"范围已确认：级别 {'/'.join(plan['change_levels']) or '—'} · 重跑阶段 {plan['stages_to_rerun']} · 回归 {plan['regression_pages'] or '无'}"},
    ]
    return RevisionResult(ok=True, status="running", next_stage=plan["stages_to_rerun"][0], events=events)


def _apply_page_changes(db: Database, project_id: int, revision_id: int, analysis: dict, plan: dict) -> None:
    """页面级登记：新增/修改/删除落到 pages 表（生命周期 + 来源 revision 可追溯）。"""
    added_names = {p.get("page_id"): (p.get("name") or p.get("page_id")) for p in (analysis.get("pages") or {}).get("added", [])}
    for pid in plan["pages"]["added"]:
        name = added_names.get(pid, pid)
        db.execute(
            "INSERT INTO pages (project_id, page_id, name, lifecycle, status, origin_revision_id, last_revision_id) "
            "VALUES (?,?,?,'added','live',?,?) "
            "ON CONFLICT(project_id, page_id) DO UPDATE SET name=excluded.name, lifecycle='added', status='live', "
            "origin_revision_id=excluded.origin_revision_id, last_revision_id=excluded.last_revision_id, updated_at=datetime('now','localtime')",
            (project_id, pid, name, revision_id, revision_id),
        )
    for pid in plan["pages"]["modified"]:
        db.execute(
            "UPDATE pages SET lifecycle='modified', last_revision_id=?, updated_at=datetime('now','localtime') "
            "WHERE project_id=? AND page_id=?",
            (revision_id, project_id, pid),
        )
    for pid in plan["pages"]["removed"]:
        db.execute(
            "UPDATE pages SET lifecycle='removed', status='removed', last_revision_id=?, updated_at=datetime('now','localtime') "
            "WHERE project_id=? AND page_id=?",
            (revision_id, project_id, pid),
        )


# ---------- revision 阶段决策（step 语义：增量变更一律显式拍板） ----------

def decide_revision_stage(
    db: Database, ws: WorkspaceManager, project_id: int, revision_id: int, stage: int,
    answers: list[AnswerIn], reason: str = "", confirm_exemptions: bool = False,
) -> RevisionResult:
    from ..stages.registry import REGISTRY  # 延迟导入防环

    revision = _revision(db, project_id, revision_id)
    if revision["status"] != "running":
        raise RevisionError(f"revision 不在增量执行状态（当前：{revision['status']}）")
    status_map = parse_json_or(revision["stage_status"], {})
    if status_map.get(str(stage)) != "awaiting_decision":
        raise RevisionError(f"revision 阶段 {stage} 不在待决策状态（当前：{status_map.get(str(stage))}）")
    card = REGISTRY.get(stage)
    if card is None:
        raise RevisionError(f"阶段 {stage} 无任务卡")
    project = db.one("SELECT design_mode, product_id FROM projects WHERE id=?", (project_id,))
    rdir = ws.revision_dir(project_id, revision_id, project["product_id"])
    if not answers:
        raise AdvanceError("决策内容为空（拍板不能是空操作）")
    answers, _ = validate_stage_decision(card, rdir, project["design_mode"], answers, [], confirm_exemptions)

    for a in answers:
        db.execute(
            "INSERT INTO decisions (project_id, revision_id, stage, question_id, question, answer, source, reason) "
            "VALUES (?,?,?,?,?,?, 'form', ?)",
            (project_id, revision_id, stage, a.id, a.id, a.answer, reason or f"revision R{revision['seq']} 阶段 {stage} 拍板"),
        )

    seq = len(list((rdir / "snapshots").glob("#*"))) + 1
    ws.snapshot(rdir, seq, stage, reason=f"revision R{revision['seq']} 阶段 {stage} 确认")
    db.execute(
        "UPDATE tasks SET state='completed', updated_at=datetime('now','localtime') WHERE revision_id=? AND stage=? AND state='awaiting_decision'",
        (revision_id, stage),
    )
    status_map[str(stage)] = "done"
    remaining = sorted(int(k) for k, v in status_map.items() if v != "done")
    next_stage = remaining[0] if remaining else None
    new_status = "completed" if next_stage is None else "running"
    if next_stage is not None:
        status_map[str(next_stage)] = "ready"
    db.execute(
        "UPDATE revisions SET status=?, stage_status=?, updated_at=datetime('now','localtime') WHERE id=?",
        (new_status, json.dumps(status_map), revision_id),
    )
    events = [
        {"type": "decision_recorded", "project_id": project_id, "revision_id": revision_id, "stage": stage,
         "answers": [{"id": a.id, "answer": a.answer} for a in answers], "source": "form"},
        {"type": "revision_state", "project_id": project_id, "revision_id": revision_id, "status": new_status,
         "detail": f"revision R{revision['seq']} 阶段 {stage} 拍板 · 快照 #{seq} · "
                   + ("全部受影响阶段完成，可合并" if new_status == "completed" else f"解锁阶段 {next_stage}")},
    ]
    return RevisionResult(ok=True, status=new_status, next_stage=next_stage, snapshot_seq=seq, events=events)


# ---------- 合并 ----------

def merge_revision(db: Database, ws: WorkspaceManager, project_id: int, revision_id: int, reason: str = "") -> RevisionResult:
    """合并：变更记录节 → 契约校验 → 拷回项目工作区 → 项目快照 → 页面收口 → 版本号。"""
    revision = _revision(db, project_id, revision_id)
    if revision["status"] != "completed":
        raise RevisionError(f"revision 尚未完成受影响阶段（当前：{revision['status']}；完成后才能合并）")
    project = db.one("SELECT * FROM projects WHERE id=?", (project_id,))
    project_dir = ws.project_dir(project_id, project["product_id"])
    rdir = ws.revision_dir(project_id, revision_id, project["product_id"])
    impact = parse_json_or(revision["impact"], {}) or {}
    plan = impact.get("plan") or {}
    if not plan:
        raise RevisionError("执行计划缺失（确认范围后才能合并）")

    for contract in ("09-spec.md", "06-tokens.json", "07-hifi"):
        if not (rdir / contract).exists():
            raise RevisionError(f"契约件缺失：{contract}（revision 未产出完整契约，不允许合并）")

    base = db.one("SELECT seq FROM snapshots WHERE id=?", (revision["base_snapshot_id"],))
    old_version = project["contract_version"]
    new_version = f"v{old_version + 1}"
    _append_change_record(rdir, revision, plan, base["seq"] if base else "?", old_version, new_version, reason)

    # 拷回项目：revision 的全部阶段产物（00-requirement.md 保留项目现状——产品文档母本可能已更新）
    for p in sorted(rdir.iterdir()):
        if p.name in _REVISION_ONLY_FILES or p.name.startswith(".") or p.name in ("snapshots", "revisions", "00-requirement.md"):
            continue
        dest = project_dir / p.name
        if p.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(p, dest)
        else:
            shutil.copy2(p, dest)

    seq = len(db.query("SELECT id FROM snapshots WHERE project_id=?", (project_id,))) + 1
    snap_dir = ws.snapshot(project_dir, seq, 9, reason=f"revision R{revision['seq']} 合并 → {new_version}")
    db.execute(
        "INSERT INTO snapshots (project_id, seq, stage, reason, dir) VALUES (?,?,?,?,?)",
        (project_id, seq, 9, f"revision R{revision['seq']} 合并（{revision['title']}）→ {new_version}", str(snap_dir)),
    )
    db.execute(
        "UPDATE revisions SET status='merged', version=?, updated_at=datetime('now','localtime') WHERE id=?",
        (new_version, revision_id),
    )
    db.execute(
        "UPDATE projects SET contract_version=?, updated_at=datetime('now','localtime') WHERE id=?",
        (old_version + 1, project_id),
    )
    db.execute(
        "INSERT INTO decisions (project_id, revision_id, stage, question_id, question, answer, source, reason) "
        "VALUES (?,?, 9, 'revision-merge', '合并设计变更', ?, 'revision_merge', ?)",
        (project_id, revision_id,
         f"已核对变更记录/受影响页面/回归结果与版本号 {new_version}，确认合并",
         reason or f"revision R{revision['seq']}《{revision['title']}》合并，基线快照 #{base['seq'] if base else '?'} → {new_version}"),
    )
    events = [
        {"type": "revision_state", "project_id": project_id, "revision_id": revision_id, "status": "merged",
         "detail": f"revision R{revision['seq']} 已合并 → {new_version} · 项目快照 #{seq}"},
        {"type": "snapshot_created", "project_id": project_id, "stage": 9, "seq": seq},
    ]
    return RevisionResult(ok=True, status="merged", snapshot_seq=seq, version=new_version, events=events)


def _append_change_record(rdir: Path, revision: dict, plan: dict, base_seq: int, old_version: int, new_version: str, reason: str) -> None:
    """09-spec.md 追加「变更记录」节（服务端确定性写入：基线/变更摘要/受影响页面/回归结果/版本号）。"""
    pages = plan.get("pages") or {}
    analysis = (parse_json_or(revision["impact"], {}) or {}).get("analysis") or {}
    regression = plan.get("regression_pages") or []
    lines = [
        "", "---", "",
        f"## 变更记录 · revision R{revision['seq']}《{revision['title']}》（{new_version}）", "",
        f"- **基线**：快照 #{base_seq} · 契约版本 v{old_version} → **{new_version}**",
        f"- **变更摘要**：{analysis.get('summary') or revision['title']}",
        f"- **变更级别**：{'、'.join(plan.get('change_levels') or []) or '—'}（重跑阶段 {plan.get('stages_to_rerun')}）",
        f"- **受影响页面**：新增 {'、'.join(pages.get('added') or []) or '无'} · "
        f"修改 {'、'.join(pages.get('modified') or []) or '无'} · 删除 {'、'.join(pages.get('removed') or []) or '无'}",
        f"- **回归结果**：" + ("；".join(f"{p}=基线产物保留·回归通过（未重做）" for p in regression) if regression else "无关联页面需回归"),
        f"- **需求来源**：{revision['doc_name'] or '直接输入'}{(' · ' + reason) if reason else ''}",
        "",
    ]
    spath = rdir / "09-spec.md"
    spath.write_text(spath.read_text(encoding="utf-8").rstrip("\n") + "\n" + "\n".join(lines), encoding="utf-8")


# ---------- 废弃 / 恢复 ----------

def discard_revision(db: Database, project_id: int, revision_id: int, reason: str = "") -> RevisionResult:
    revision = _revision(db, project_id, revision_id)
    if revision["status"] == "merged":
        raise RevisionError("已合并的 revision 不可废弃（历史不可篡改；如需回退用快照恢复）")
    db.execute(
        "UPDATE revisions SET status='discarded', updated_at=datetime('now','localtime') WHERE id=?",
        (revision_id,),
    )
    # 已登记的页面变更回退：新增页撤录（先删，避免被下面的 UPDATE 清掉 last_revision_id）、修改/删除还原
    db.execute(
        "DELETE FROM pages WHERE project_id=? AND origin_revision_id=? AND last_revision_id=?",
        (project_id, revision_id, revision_id),
    )
    db.execute(
        "UPDATE pages SET status='live', lifecycle=CASE WHEN origin_revision_id IS NULL THEN 'initial' ELSE 'added' END, "
        "last_revision_id=NULL WHERE project_id=? AND last_revision_id=? AND lifecycle!='removed'",
        (project_id, revision_id),
    )
    return RevisionResult(ok=True, status="discarded", events=[
        {"type": "revision_state", "project_id": project_id, "revision_id": revision_id, "status": "discarded",
         "detail": f"revision R{revision['seq']} 已废弃（工作区保留可查）{(' · ' + reason) if reason else ''}"},
    ])


def restore_project_snapshot(db: Database, ws: WorkspaceManager, project_id: int, seq: int, reason: str = "") -> RevisionResult:
    """项目工作区恢复为快照 #seq：先保全当前状态，再还原（快照本体与 revisions/ 不动）。"""
    project = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    if project is None:
        raise RevisionError(f"项目不存在：{project_id}")
    active = db.query(
        "SELECT id, seq, status FROM revisions WHERE project_id=? AND status IN ('analyzing','impact_ready','running')",
        (project_id,),
    )
    if active:
        raise RevisionError(f"存在进行中的 revision（R{active[0]['seq']} {active[0]['status']}）——先废弃或合并再恢复快照")
    project_dir = ws.project_dir(project_id, project["product_id"])
    safety_seq = len(db.query("SELECT id FROM snapshots WHERE project_id=?", (project_id,))) + 1
    ws.restore_snapshot(project_dir, seq, safety_seq)
    db.execute(
        "INSERT INTO snapshots (project_id, seq, stage, reason, dir) VALUES (?,?,0,?,?)",
        (project_id, safety_seq, f"回退至 #{seq} 前的自动保全", str(project_dir / "snapshots" / f"#{safety_seq}")),
    )
    db.execute(
        "INSERT INTO decisions (project_id, stage, question_id, question, answer, source, reason) "
        "VALUES (?,?, 'snapshot-rollback', '恢复历史快照', ?, 'rollback', ?)",
        (project_id, 0, f"工作区还原为快照 #{seq}", reason or None),
    )
    return RevisionResult(ok=True, snapshot_seq=safety_seq, events=[
        {"type": "snapshot_created", "project_id": project_id, "stage": 0, "seq": safety_seq},
        {"type": "task_state", "project_id": project_id, "stage": 0, "state": "completed",
         "detail": f"项目工作区已恢复为快照 #{seq}（当前状态保全为 #{safety_seq}）"},
    ])


# ---------- 查询 ----------

def _revision(db: Database, project_id: int, revision_id: int) -> dict[str, Any]:
    revision = db.one("SELECT * FROM revisions WHERE id=? AND project_id=?", (revision_id, project_id))
    if revision is None:
        raise RevisionError(f"revision 不存在：{revision_id}")
    return revision


def revision_diff(ws: WorkspaceManager, project_id: int, revision_id: int, base_snapshot_dir: Path, revision_dir: Path) -> dict[str, Any]:
    """基线快照 vs revision 工作区：契约与阶段产物差异（sha256 逐文件比对）。"""
    def manifest(root: Path) -> dict[str, str]:
        out: dict[str, str] = {}
        if not root.is_dir():
            return out
        for p in root.rglob("*"):
            if not p.is_file() or p.name.startswith(".") or p.suffix not in (".md", ".html", ".json"):
                continue
            rel = str(p.relative_to(root))
            if rel.split("/")[0] in ("snapshots", "revisions") or rel in _REVISION_ONLY_FILES:
                continue
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        return out

    base_m, rev_m = manifest(base_snapshot_dir), manifest(revision_dir)
    return {
        "added": sorted(set(rev_m) - set(base_m)),
        "changed": sorted(k for k in set(rev_m) & set(base_m) if rev_m[k] != base_m[k]),
        "removed": sorted(set(base_m) - set(rev_m)),
        "unchanged_count": sum(1 for k in set(rev_m) & set(base_m) if rev_m[k] == base_m[k]),
    }
