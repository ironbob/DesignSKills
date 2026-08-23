"""工作台 API：项目详情（含产物清单）、阶段任务发起、任务查询、决策数据读取。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import Database, parse_json_or
from ..deps import get_db, get_ws
from ..engine.advance import AdvanceError, AnswerIn, DefaultIn, advance_stage, final_acceptance
from ..engine.queue import TaskError
from ..platforms import PLATFORMS
from ..stages.registry import DECISION_META, NINE_STAGES, REGISTRY, crit_decision_items, gallery_items
from ..workspace import WorkspaceManager

router = APIRouter(prefix="/api")


def _project_payload(db: Database, project_id: int) -> dict:
    row = db.one(
        "SELECT p.*, pr.name AS product_name FROM projects p JOIN products pr ON pr.id=p.product_id WHERE p.id=?",
        (project_id,),
    )
    if row is None:
        raise HTTPException(404, f"项目不存在：{project_id}")
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "name": row["name"],
        "platform": row["platform"],
        "platform_label": PLATFORMS[row["platform"]]["label"],
        "canvas": {"width": row["canvas_w"], "height": row["canvas_h"]},
        "run_mode": row["run_mode"],
        "design_mode": row["design_mode"],
        "current_stage": row["current_stage"],
        "stage_status": parse_json_or(row["stage_status"], {}),
        "decision_meta": {str(k): v for k, v in DECISION_META.items()},
        "decision_types": {str(k): v.decision_type for k, v in REGISTRY.items()},
        "updated_at": row["updated_at"],
    }


def _list_artifacts(project_dir: Path) -> list[dict]:
    items: list[dict] = []
    for p in sorted(project_dir.rglob("*")):
        rel = p.relative_to(project_dir)
        if not p.is_file() or rel.parts[0] == "snapshots" or rel.name.startswith("."):
            continue
        if p.suffix in (".md", ".html", ".json"):
            items.append({
                "path": str(rel),
                "kind": p.suffix.lstrip("."),
                "mtime": int(p.stat().st_mtime),
            })
    return items


@router.get("/projects/{project_id}")
def project_detail(project_id: int, db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws)):
    payload = _project_payload(db, project_id)
    project_dir = ws.project_dir(project_id, payload["product_id"])
    payload["artifacts"] = _list_artifacts(project_dir)
    payload["stage_names"] = NINE_STAGES
    task = db.one("SELECT * FROM tasks WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,))
    payload["current_task"] = task
    return payload


@router.post("/projects/{project_id}/stages/{stage}/tasks", status_code=201)
def create_stage_task(project_id: int, stage: int, request: Request, db: Database = Depends(get_db)):
    _project_payload(db, project_id)  # 404 校验
    try:
        task_id = request.app.state.engine.enqueue_stage_task(project_id, stage)
    except TaskError as e:
        raise HTTPException(409, str(e)) from e
    return {"task_id": task_id}


@router.get("/projects/{project_id}/tasks/current")
def current_task(project_id: int, db: Database = Depends(get_db)):
    task = db.one("SELECT * FROM tasks WHERE project_id=? ORDER BY id DESC LIMIT 1", (project_id,))
    return task or {}


@router.get("/projects/{project_id}/decision/{stage}")
def decision_data(project_id: int, stage: int, db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws)):
    payload = _project_payload(db, project_id)
    card = REGISTRY.get(stage)
    if card is None:
        raise HTTPException(404, f"阶段 {stage} 无任务卡")
    if card.decision_type == "confirm":
        return {"type": "confirm", "stage": stage, "stage_name": card.name}
    project_dir = ws.project_dir(project_id, payload["product_id"])
    if card.decision_type == "gallery":
        items = gallery_items(card, project_dir)
        if not items or not any(it.get("options") for it in items):
            raise HTTPException(404, "决策数据尚未产出（先完成阶段任务）")
        return {"type": "gallery", "stage": stage, "stage_name": card.name, "data": {"items": items}}
    qpath = project_dir / (card.decision_data_path or "")
    if not qpath.exists():
        raise HTTPException(404, "决策数据尚未产出（先完成阶段任务）")
    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
    except ValueError as e:
        raise HTTPException(502, f"决策数据不可解析：{e}") from e
    if card.decision_type == "crit":
        yellows, u_items = crit_decision_items(data)
        data = {"yellows": yellows, "u_items": u_items}
    return {"type": card.decision_type, "stage": stage, "stage_name": card.name, "data": data}


# ---------- 决策提交：台账 + 快照 + 解锁（R1/R3/R6；引擎 auto 代批共用 advance service） ----------

class DecisionAnswer(BaseModel):
    id: str
    answer: str  # 选中的 label / 确认文案


class DecisionIn(BaseModel):
    answers: list[DecisionAnswer] = []
    accepted_defaults: list[dict] = []  # {id, text, value}
    reason: str = ""
    confirm_exemptions: bool = False  # crit 豁免处置的显式人工确认


@router.post("/projects/{project_id}/stages/{stage}/decision")
def submit_decision(
    project_id: int,
    stage: int,
    payload: DecisionIn,
    request: Request,
    db: Database = Depends(get_db),
    ws: WorkspaceManager = Depends(get_ws),
):
    bus = request.app.state.bus
    try:
        result = advance_stage(
            db, ws, project_id, stage,
            answers=[AnswerIn(a.id, a.answer) for a in payload.answers],
            accepted_defaults=[DefaultIn(d.get("id", "B-x"), d.get("text", "默认假设"), d.get("value", "")) for d in payload.accepted_defaults],
            reason=payload.reason,
            source="form",
            confirm_exemptions=payload.confirm_exemptions,
        )
    except AdvanceError as e:
        # 未答全/处置非法/豁免未确认→422；状态错→409（保持原 API 语义）
        if "未答全" in str(e) or "非法" in str(e) or "豁免" in str(e):
            raise HTTPException(422, str(e)) from e
        raise HTTPException(409, str(e)) from e
    for ev in result.events:
        bus.publish(ev.pop("type"), **ev)
    return {"ok": True, "next_stage": result.next_stage, "snapshot_seq": result.snapshot_seq}


@router.get("/projects/{project_id}/ledger")
def ledger(project_id: int, db: Database = Depends(get_db)):
    rows = db.query("SELECT * FROM decisions WHERE project_id=? ORDER BY id", (project_id,))
    snaps = db.query("SELECT seq, stage, reason, created_at FROM snapshots WHERE project_id=? ORDER BY seq", (project_id,))
    reviews = db.query(
        "SELECT stage, attempt, verdict, red_count, yellow_count, created_at FROM reviews WHERE project_id=? ORDER BY id",
        (project_id,),
    )
    project = db.one("SELECT run_mode, design_mode FROM projects WHERE id=?", (project_id,))
    return {
        "run_mode": project["run_mode"] if project else None,
        "design_mode": project["design_mode"] if project else None,
        "decisions": rows, "snapshots": snaps, "reviews": reviews,
    }


# ---------- rapid 最终验收：整体验收/导出确认（一次，替代回退 4/5 的多轮选择） ----------

@router.get("/projects/{project_id}/acceptance")
def acceptance_data(project_id: int, db: Database = Depends(get_db), ws: WorkspaceManager = Depends(get_ws)):
    payload = _project_payload(db, project_id)
    status = payload["stage_status"].get("9")
    if status != "awaiting_acceptance":
        raise HTTPException(409, f"项目不在最终验收状态（阶段 9 当前：{status}）")
    project_dir = ws.project_dir(project_id, payload["product_id"])
    try:
        jdata = json.loads((project_dir / ".stage8-findings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise HTTPException(502, f"crit 决策数据不可读：{e}") from e
    yellows, u_items = crit_decision_items(jdata)
    defaults = db.query(
        "SELECT stage, question_id, question, answer, reason, created_at FROM decisions "
        "WHERE project_id=? AND source='rapid_default' ORDER BY id",
        (project_id,),
    )
    contract = [
        a for a in _list_artifacts(project_dir)
        if a["path"] == "09-spec.md" or a["path"] == "06-tokens.json" or a["path"].startswith("07-hifi/")
    ]
    return {
        "design_mode": payload["design_mode"],
        "spec": "09-spec.md",
        "contract_files": contract,
        "default_decisions": defaults,
        "u_items": u_items,
        "yellow_dispositions": [
            {"id": f["id"], "dim": f.get("dim"), "evidence": f.get("evidence"), "disposition": f.get("proposed")}
            for f in yellows
        ],
    }


class AcceptanceIn(BaseModel):
    reason: str = ""


@router.post("/projects/{project_id}/acceptance")
def submit_acceptance(
    project_id: int,
    payload: AcceptanceIn,
    request: Request,
    db: Database = Depends(get_db),
    ws: WorkspaceManager = Depends(get_ws),
):
    bus = request.app.state.bus
    try:
        result = final_acceptance(db, ws, project_id, reason=payload.reason)
    except AdvanceError as e:
        raise HTTPException(409, str(e)) from e
    for ev in result.events:
        bus.publish(ev.pop("type"), **ev)
    return {"ok": True, "snapshot_seq": result.snapshot_seq}
