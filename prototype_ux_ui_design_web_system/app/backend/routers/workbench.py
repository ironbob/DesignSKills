"""工作台 API：项目详情（含产物清单）、阶段任务发起、任务查询、决策数据读取。"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..db import Database, parse_json_or
from ..deps import get_db, get_ws
from ..engine.queue import TaskError
from ..platforms import PLATFORMS
from ..stages.registry import NINE_STAGES, REGISTRY
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
        "current_stage": row["current_stage"],
        "stage_status": parse_json_or(row["stage_status"], {}),
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
    qpath = project_dir / (card.decision_data_path or "")
    if not qpath.exists():
        raise HTTPException(404, "决策数据尚未产出（先完成阶段任务）")
    try:
        data = json.loads(qpath.read_text(encoding="utf-8"))
    except ValueError as e:
        raise HTTPException(502, f"决策数据不可解析：{e}") from e
    return {"type": card.decision_type, "stage": stage, "stage_name": card.name, "data": data}


# ---------- 决策提交：台账 + 快照 + 解锁（R1/R3/R6） ----------

class DecisionAnswer(BaseModel):
    id: str
    answer: str  # 选中的 label / 确认文案


class DecisionIn(BaseModel):
    answers: list[DecisionAnswer] = []
    accepted_defaults: list[dict] = []  # {id, text, value}
    reason: str = ""


def _set_stage_map(db: Database, project_id: int, mut: dict[str, str]) -> None:
    row = db.one("SELECT stage_status FROM projects WHERE id=?", (project_id,))
    m: dict[str, str] = parse_json_or(row["stage_status"], {})
    m.update(mut)
    db.execute(
        "UPDATE projects SET stage_status=?, updated_at=datetime('now','localtime') WHERE id=?",
        (json.dumps(m, ensure_ascii=False), project_id),
    )


@router.post("/projects/{project_id}/stages/{stage}/decision")
def submit_decision(
    project_id: int,
    stage: int,
    payload: DecisionIn,
    request: Request,
    db: Database = Depends(get_db),
    ws: WorkspaceManager = Depends(get_ws),
):
    detail = _project_payload(db, project_id)
    card = REGISTRY.get(stage)
    if card is None:
        raise HTTPException(404, f"阶段 {stage} 无任务卡")
    if detail["stage_status"].get(str(stage)) != "awaiting_decision":
        raise HTTPException(409, f"阶段 {stage} 不在待决策状态（当前：{detail['stage_status'].get(str(stage))}）")

    # 硬校验（gate 的决策侧）：question_form 必须全答
    if card.decision_type == "question_form":
        project_dir = ws.project_dir(project_id, detail["product_id"])
        data = json.loads((project_dir / (card.decision_data_path or "")).read_text(encoding="utf-8"))
        required = {q["id"] for q in data.get("blocking", [])}
        answered = {a.id for a in payload.answers}
        missing = required - answered
        if missing:
            raise HTTPException(422, f"阻塞问题未答全（零裸答与零裸问对称）：{sorted(missing)}")

    # 台账（R3）
    for a in payload.answers:
        db.execute(
            "INSERT INTO decisions (project_id, stage, question_id, question, answer, source, reason) VALUES (?,?,?,?,?,?,?)",
            (project_id, stage, a.id, a.id, a.answer, card.decision_type, payload.reason or None),
        )
    for d in payload.accepted_defaults:
        db.execute(
            "INSERT INTO decisions (project_id, stage, question_id, question, answer, source) VALUES (?,?,?,?,?,?)",
            (project_id, stage, d.get("id", "B-x"), d.get("text", "默认假设"), d.get("value", ""), "defaults"),
        )

    # 快照（R6）+ 任务完结 + 解锁下一阶段（R1）
    seq = len(db.query("SELECT id FROM snapshots WHERE project_id=?", (project_id,))) + 1
    project_dir = ws.project_dir(project_id, detail["product_id"])
    snap_dir = ws.snapshot(project_dir, seq, stage)
    db.execute(
        "INSERT INTO snapshots (project_id, seq, stage, reason, dir) VALUES (?,?,?,?,?)",
        (project_id, seq, stage, payload.reason or f"阶段 {stage} 确认", str(snap_dir)),
    )
    db.execute("UPDATE tasks SET state='completed', updated_at=datetime('now','localtime') WHERE project_id=? AND stage=? AND state='awaiting_decision'", (project_id, stage))

    mut: dict[str, str] = {str(stage): "done"}
    next_stage = stage + 1 if stage < 9 else stage
    if stage < 9:
        mut[str(next_stage)] = "ready"
    _set_stage_map(db, project_id, mut)
    db.execute("UPDATE projects SET current_stage=?, updated_at=datetime('now','localtime') WHERE id=?", (next_stage, project_id))

    bus = request.app.state.bus
    bus.publish("decision_recorded", project_id=project_id, stage=stage, answers=[a.model_dump() for a in payload.answers])
    bus.publish("snapshot_created", project_id=project_id, stage=stage, seq=seq)
    bus.publish("task_state", project_id=project_id, stage=stage, state="completed", detail=f"阶段 {stage} 拍板 · 快照 #{seq} · 解锁阶段 {next_stage}")

    return {"ok": True, "next_stage": next_stage, "snapshot_seq": seq}


@router.get("/projects/{project_id}/ledger")
def ledger(project_id: int, db: Database = Depends(get_db)):
    rows = db.query("SELECT * FROM decisions WHERE project_id=? ORDER BY id", (project_id,))
    snaps = db.query("SELECT seq, stage, reason, created_at FROM snapshots WHERE project_id=? ORDER BY seq", (project_id,))
    return {"decisions": rows, "snapshots": snaps}
