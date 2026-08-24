"""增量设计变更 API：revision 全生命周期 + 快照查看/恢复 + 基线↔revision 差异。

入口语义（SKILL 增量章节的工具化映射）：
- 创建 revision = 提交新需求/需求变更（建后只跑阶段 0 影响分析，绝不立即整轮重跑）；
- 确认范围 = 用户拍板影响分析 → 解锁受影响阶段（revision 独立状态机）；
- 合并 = 新契约带回项目工作区 + 项目快照 + 版本号（历史快照与原项目产物在此之前只读）。
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..db import Database, parse_json_or
from ..deps import get_db, get_ws
from ..engine.advance import AdvanceError, AnswerIn
from ..engine.queue import TaskError
from ..engine.revision import (
    RevisionError,
    confirm_scope,
    create_revision,
    decide_revision_stage,
    discard_revision,
    merge_revision,
    restore_project_snapshot,
    revision_diff,
)
from ..stages.registry import REVISION_STAGE_NAMES, REGISTRY, crit_decision_items, gallery_items
from ..workspace import WorkspaceError, WorkspaceManager

router = APIRouter(prefix="/api")

MEDIA = {".html": "text/html", ".md": "text/plain; charset=utf-8", ".json": "application/json", ".txt": "text/plain; charset=utf-8"}


class RevisionCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    requirement_text: str = Field(min_length=1)
    doc_name: str | None = None
    reason: str = ""
    base_snapshot_id: int | None = None


class ScopeConfirmIn(BaseModel):
    reason: str = ""


class RevisionDecisionIn(BaseModel):
    answers: list[dict] = []
    reason: str = ""
    confirm_exemptions: bool = False


class MergeIn(BaseModel):
    reason: str = ""


class RestoreIn(BaseModel):
    reason: str = ""


def _publish(request: Request, events: list[dict]) -> None:
    bus = request.app.state.bus
    for ev in events:
        bus.publish(ev.pop("type"), **ev)


def _revision_or_404(db: Database, project_id: int, revision_id: int) -> dict:
    row = db.one("SELECT * FROM revisions WHERE id=? AND project_id=?", (revision_id, project_id))
    if row is None:
        raise HTTPException(404, f"revision 不存在：{revision_id}")
    return row


def _base_snapshot(db: Database, revision: dict) -> dict:
    snap = db.one("SELECT seq, stage, reason, created_at FROM snapshots WHERE id=?", (revision["base_snapshot_id"],))
    return snap or {"seq": "?", "stage": None, "reason": None, "created_at": None}


def _revision_payload(db: Database, ws: WorkspaceManager, row: dict, *, detail: bool = False) -> dict:
    project = db.one("SELECT product_id FROM projects WHERE id=?", (row["project_id"],))
    base = _base_snapshot(db, row)
    payload = {
        "id": row["id"],
        "project_id": row["project_id"],
        "seq": row["seq"],
        "title": row["title"],
        "doc_name": row["doc_name"],
        "reason": row["reason"],
        "base_snapshot_id": row["base_snapshot_id"],
        "base_snapshot_seq": base["seq"],
        "status": row["status"],
        "change_levels": parse_json_or(row["change_levels"], []),
        "version": row["version"],
        "stage_status": parse_json_or(row["stage_status"], {}),
        "stage_names": REVISION_STAGE_NAMES,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if detail:
        impact = parse_json_or(row["impact"], {})
        payload["impact"] = impact.get("analysis") if impact else None
        payload["plan"] = impact.get("plan") if impact else None
        payload["tasks"] = db.query(
            "SELECT * FROM tasks WHERE revision_id=? ORDER BY id", (row["id"],),
        )
        payload["decisions"] = db.query(
            "SELECT * FROM decisions WHERE revision_id=? ORDER BY id", (row["id"],),
        )
        rdir = ws.revision_dir(row["project_id"], row["id"], project["product_id"])
        payload["artifacts"] = _list_revision_artifacts(rdir)
        # 当前阶段（stage 图里最新非 done 的；否则最高已完成阶段）
        pend = sorted(int(k) for k, v in payload["stage_status"].items() if v not in ("done", "locked"))
        payload["current_stage"] = pend[0] if pend else max((int(k) for k in payload["stage_status"]), default=0)
        payload["current_task"] = db.one(
            "SELECT * FROM tasks WHERE revision_id=? ORDER BY id DESC LIMIT 1", (row["id"],),
        )
    return payload


def _list_revision_artifacts(rdir: Path) -> list[dict]:
    if not rdir.is_dir():
        return []
    items: list[dict] = []
    for p in sorted(rdir.rglob("*")):
        rel = p.relative_to(rdir)
        if not p.is_file() or rel.parts[0] == "snapshots" or rel.name.startswith("."):
            continue
        if p.suffix in (".md", ".html", ".json"):
            items.append({"path": str(rel), "kind": p.suffix.lstrip("."), "mtime": int(p.stat().st_mtime)})
    return items


# ---------- 创建 / 列表 / 详情 ----------

@router.get("/projects/{project_id}/revisions")
def list_revisions(project_id: int, db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws)):
    rows = db.query("SELECT * FROM revisions WHERE project_id=? ORDER BY seq", (project_id,))
    return [_revision_payload(db, ws, r) for r in rows]


@router.post("/projects/{project_id}/revisions", status_code=201)
def create_revision_route(
    project_id: int, payload: RevisionCreateIn, request: Request,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    try:
        revision = create_revision(
            db, ws, project_id, payload.title, payload.requirement_text,
            payload.doc_name, payload.reason, payload.base_snapshot_id,
        )
    except RevisionError as e:
        raise HTTPException(409, str(e)) from e
    # 创建即入队阶段 0（影响分析）——不重跑任何设计阶段
    try:
        request.app.state.engine.enqueue_revision_stage_task(project_id, revision["id"], 0)
    except TaskError as e:  # 队列未就绪等基础设施问题：revision 已建，UI 可手动重试阶段 0
        raise HTTPException(503, f"影响分析任务入队失败（revision 已创建，可重试）：{e}") from e
    return _revision_payload(db, ws, db.one("SELECT * FROM revisions WHERE id=?", (revision["id"],)), detail=True)


@router.get("/projects/{project_id}/revisions/{revision_id}")
def revision_detail(project_id: int, revision_id: int, db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws)):
    row = _revision_or_404(db, project_id, revision_id)
    return _revision_payload(db, ws, row, detail=True)


@router.get("/projects/{project_id}/revisions/{revision_id}/impact")
def revision_impact(project_id: int, revision_id: int, db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws)):
    """影响分析 + 确定性执行计划。impact_ready 前后都可查（plan 实时推导，confirm 后锁定）。"""
    from ..engine.impact import load_impact, plan_from_impact

    row = _revision_or_404(db, project_id, revision_id)
    project = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    rdir = ws.revision_dir(project_id, revision_id, project["product_id"])
    analysis = load_impact(rdir)
    if analysis is None:
        return {"ready": False, "status": row["status"]}
    locked = parse_json_or(row["impact"], {}) or {}
    return {
        "ready": True,
        "status": row["status"],
        "analysis": analysis,
        "plan": (locked.get("plan") if locked.get("plan") else plan_from_impact(analysis)),
        "locked": bool(locked.get("plan")),
        "impact_md": "00-impact.md" if (rdir / "00-impact.md").exists() else None,
    }


# ---------- 确认范围 / 废弃 ----------

@router.post("/projects/{project_id}/revisions/{revision_id}/confirm")
def confirm_revision_scope(
    project_id: int, revision_id: int, payload: ScopeConfirmIn, request: Request,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    try:
        result = confirm_scope(db, ws, project_id, revision_id, reason=payload.reason)
    except RevisionError as e:
        raise HTTPException(409, str(e)) from e
    _publish(request, result.events)
    if result.next_stage is not None:
        try:
            request.app.state.engine.enqueue_revision_stage_task(project_id, revision_id, result.next_stage)
        except TaskError as e:
            raise HTTPException(503, f"范围已确认，但阶段 {result.next_stage} 入队失败（可手动发起）：{e}") from e
    return {"ok": True, "status": result.status, "next_stage": result.next_stage}


@router.post("/projects/{project_id}/revisions/{revision_id}/discard")
def discard_revision_route(
    project_id: int, revision_id: int, payload: ScopeConfirmIn, request: Request,
    db: Database = Depends(get_db),
):
    try:
        result = discard_revision(db, project_id, revision_id, reason=payload.reason)
    except RevisionError as e:
        raise HTTPException(409, str(e)) from e
    _publish(request, result.events)
    return {"ok": True, "status": result.status}


# ---------- 增量任务 / 决策 ----------

@router.post("/projects/{project_id}/revisions/{revision_id}/stages/{stage}/tasks", status_code=201)
def create_revision_stage_task(
    project_id: int, revision_id: int, stage: int, request: Request,
    db: Database = Depends(get_db),
):
    _revision_or_404(db, project_id, revision_id)
    try:
        task_id = request.app.state.engine.enqueue_revision_stage_task(project_id, revision_id, stage)
    except TaskError as e:
        raise HTTPException(409, str(e)) from e
    return {"task_id": task_id}


@router.get("/projects/{project_id}/revisions/{revision_id}/decision/{stage}")
def revision_decision_data(
    project_id: int, revision_id: int, stage: int,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    row = _revision_or_404(db, project_id, revision_id)
    card = REGISTRY.get(stage)
    if card is None:
        raise HTTPException(404, f"阶段 {stage} 无任务卡")
    project = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    rdir = ws.revision_dir(project_id, revision_id, project["product_id"])
    if card.decision_type == "confirm":
        return {"type": "confirm", "stage": stage, "stage_name": card.name}
    if card.decision_type == "gallery":
        items = gallery_items(card, rdir)
        if not items or not any(it.get("options") for it in items):
            raise HTTPException(404, "决策数据尚未产出（先完成阶段任务）")
        return {"type": "gallery", "stage": stage, "stage_name": card.name, "data": {"items": items}}
    if card.decision_type == "crit":
        qpath = rdir / (card.decision_data_path or "")
        if not qpath.exists():
            raise HTTPException(404, "决策数据尚未产出（先完成阶段任务）")
        try:
            data = json.loads(qpath.read_text(encoding="utf-8"))
        except ValueError as e:
            raise HTTPException(502, f"决策数据不可解析：{e}") from e
        yellows, u_items = crit_decision_items(data)
        return {"type": "crit", "stage": stage, "stage_name": card.name, "data": {"yellows": yellows, "u_items": u_items}}
    raise HTTPException(409, f"阶段 {stage} 决策类型 {card.decision_type} 不走决策端点（{row['status']}）")


@router.post("/projects/{project_id}/revisions/{revision_id}/stages/{stage}/decision")
def submit_revision_decision(
    project_id: int, revision_id: int, stage: int, payload: RevisionDecisionIn, request: Request,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    try:
        result = decide_revision_stage(
            db, ws, project_id, revision_id, stage,
            answers=[AnswerIn(a.get("id", ""), a.get("answer", "")) for a in payload.answers],
            reason=payload.reason,
            confirm_exemptions=payload.confirm_exemptions,
        )
    except RevisionError as e:
        raise HTTPException(409, str(e)) from e
    except AdvanceError as e:
        raise HTTPException(422, str(e)) from e
    _publish(request, result.events)
    if result.next_stage is not None:
        try:
            request.app.state.engine.enqueue_revision_stage_task(project_id, revision_id, result.next_stage)
        except TaskError as e:
            raise HTTPException(503, f"决策已落账，但下一阶段 {result.next_stage} 入队失败（可手动发起）：{e}") from e
    return {"ok": True, "status": result.status, "next_stage": result.next_stage, "snapshot_seq": result.snapshot_seq}


# ---------- 合并 / 差异 ----------

@router.post("/projects/{project_id}/revisions/{revision_id}/merge")
def merge_revision_route(
    project_id: int, revision_id: int, payload: MergeIn, request: Request,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    try:
        result = merge_revision(db, ws, project_id, revision_id, reason=payload.reason)
    except RevisionError as e:
        raise HTTPException(409, str(e)) from e
    _publish(request, result.events)
    return {"ok": True, "status": result.status, "version": result.version, "snapshot_seq": result.snapshot_seq}


@router.get("/projects/{project_id}/revisions/{revision_id}/diff")
def revision_diff_route(
    project_id: int, revision_id: int,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    row = _revision_or_404(db, project_id, revision_id)
    project = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    project_dir = ws.project_dir(project_id, project["product_id"])
    base = _base_snapshot(db, row)
    base_dir = project_dir / "snapshots" / f"#{base['seq']}"
    rdir = ws.revision_dir(project_id, revision_id, project["product_id"])
    diff = revision_diff(ws, project_id, revision_id, base_dir, rdir)
    locked = parse_json_or(row["impact"], {}) or {}
    diff["pages"] = (locked.get("plan") or {}).get("pages") or {}
    diff["base_snapshot_seq"] = base["seq"]
    return diff


# ---------- 快照：查看 / 文件 / 恢复（历史只读） ----------

@router.get("/projects/{project_id}/snapshots")
def list_snapshots(project_id: int, db: Database = Depends(get_db)):
    return db.query(
        "SELECT s.id, s.seq, s.stage, s.reason, s.created_at, "
        "(SELECT COUNT(*) FROM revisions r WHERE r.base_snapshot_id=s.id) AS base_of_revisions "
        "FROM snapshots s WHERE s.project_id=? ORDER BY s.seq",
        (project_id,),
    )


@router.get("/projects/{project_id}/snapshots/{seq}")
def snapshot_detail(project_id: int, seq: int, db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws)):
    project = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    if project is None:
        raise HTTPException(404, f"项目不存在：{project_id}")
    row = db.one("SELECT * FROM snapshots WHERE project_id=? AND seq=?", (project_id, seq))
    if row is None:
        raise HTTPException(404, f"快照不存在：#{seq}")
    project_dir = ws.project_dir(project_id, project["product_id"])
    try:
        files = ws.snapshot_files(project_dir, seq)
    except WorkspaceError as e:
        raise HTTPException(404, str(e)) from e
    return {"seq": seq, "stage": row["stage"], "reason": row["reason"], "created_at": row["created_at"], "files": files}


@router.get("/projects/{project_id}/snapshots/{seq}/file")
def snapshot_file(
    project_id: int, seq: int, path: str,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    """快照内文件预览（只读；# 目录名不宜走 URL 路径段，故用 query 参数）。"""
    project = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    if project is None:
        raise HTTPException(404, f"项目不存在：{project_id}")
    row = db.one("SELECT id FROM snapshots WHERE project_id=? AND seq=?", (project_id, seq))
    if row is None:
        raise HTTPException(404, f"快照不存在：#{seq}")
    project_dir = ws.project_dir(project_id, project["product_id"])
    sdir = (project_dir / "snapshots" / f"#{seq}").resolve()
    try:
        fpath = ws.resolve(sdir, path)
    except WorkspaceError as e:
        raise HTTPException(404, str(e)) from e
    media = MEDIA.get(fpath.suffix.lower(), "application/octet-stream")
    return StreamingResponse(open(fpath, "rb"), media_type=media, headers={"Cache-Control": "no-cache"})


@router.post("/projects/{project_id}/snapshots/{seq}/restore")
def restore_snapshot_route(
    project_id: int, seq: int, payload: RestoreIn, request: Request,
    db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws),
):
    row = db.one("SELECT id FROM snapshots WHERE project_id=? AND seq=?", (project_id, seq))
    if row is None:
        raise HTTPException(404, f"快照不存在：#{seq}")
    try:
        result = restore_project_snapshot(db, ws, project_id, seq, reason=payload.reason)
    except RevisionError as e:
        raise HTTPException(409, str(e)) from e
    except WorkspaceError as e:
        raise HTTPException(404, str(e)) from e
    _publish(request, result.events)
    return {"ok": True, "restored_to": seq, "safety_snapshot_seq": result.snapshot_seq}
