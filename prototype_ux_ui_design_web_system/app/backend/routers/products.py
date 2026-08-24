"""产品/项目对象 API（两级对象：产品→项目锁端）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..db import Database, parse_json_or
from ..deps import get_db, get_ws
from ..platforms import PLATFORMS, is_platform
from ..workspace import WorkspaceManager

router = APIRouter(prefix="/api")


class NewProjectIn(BaseModel):
    name: str
    platform: str
    run_mode: str = "step"  # step=每阶段人审；auto=事实类阶段过双层 gate 自动推进
    design_mode: str = "deliberate"  # deliberate=精细多候选（默认）；rapid=快速单候选+默认决策（与 run_mode 正交）


class NewProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    requirement_doc: str = Field(min_length=1)
    doc_name: str = "requirements.md"
    project: NewProjectIn


def _product_payload(db: Database, row: dict) -> dict:
    projects = db.query("SELECT * FROM projects WHERE product_id=? ORDER BY id", (row["id"],))
    return {
        "id": row["id"],
        "name": row["name"],
        "requirement_doc": row["requirement_doc"],
        "requirement_updated_at": row["requirement_updated_at"],
        "updated_at": row["updated_at"],
        "projects": [
            {
                "id": p["id"],
                "name": p["name"],
                "platform": p["platform"],
                "canvas": {"width": p["canvas_w"], "height": p["canvas_h"]},
                "run_mode": p["run_mode"],
                "design_mode": p["design_mode"],
                "current_stage": p["current_stage"],
                "stage_status": parse_json_or(p["stage_status"], {}),
                "contract_version": p["contract_version"],
                "snapshot_count": db.one("SELECT COUNT(*) AS n FROM snapshots WHERE project_id=?", (p["id"],))["n"],
                "revisions": db.query(
                    "SELECT id, seq, title, status, version, updated_at FROM revisions WHERE project_id=? ORDER BY seq",
                    (p["id"],),
                ),
                "updated_at": p["updated_at"],
            }
            for p in projects
        ],
    }


@router.get("/products")
def list_products(db: Database = Depends(get_db)):
    rows = db.query("SELECT * FROM products ORDER BY updated_at DESC, id DESC")
    return [_product_payload(db, r) for r in rows]


@router.post("/products", status_code=201)
def create_product(
    payload: NewProductIn,
    db: Database = Depends(get_db),
    ws: WorkspaceManager = Depends(get_ws),
):
    if not is_platform(payload.project.platform):
        raise HTTPException(422, f"未知目标端：{payload.project.platform}")
    if payload.project.run_mode not in ("step", "auto"):
        raise HTTPException(422, f"未知推进模式：{payload.project.run_mode}")
    if payload.project.design_mode not in ("deliberate", "rapid"):
        raise HTTPException(422, f"未知设计模式：{payload.project.design_mode}")
    preset = PLATFORMS[payload.project.platform]

    product_id = db.execute(
        "INSERT INTO products (name, requirement_doc, requirement_updated_at) VALUES (?,?,datetime('now','localtime'))",
        (payload.name, payload.doc_name),
    )
    ws.create_product(product_id, payload.name, payload.doc_name, payload.requirement_doc)

    project_id = db.execute(
        "INSERT INTO projects (product_id, name, platform, canvas_w, canvas_h, run_mode, design_mode, stage_status) VALUES (?,?,?,?,?,?,?,?)",
        (product_id, payload.project.name, payload.project.platform, preset["width"], preset["height"], payload.project.run_mode, payload.project.design_mode, '{"1":"ready"}'),
    )
    ws.create_project(project_id, product_id, payload.requirement_doc, payload.doc_name)

    row = db.one("SELECT * FROM products WHERE id=?", (product_id,))
    return _product_payload(db, row)
