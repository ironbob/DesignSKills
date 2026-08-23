"""决策落账 service：台账 + 快照 + 解锁下一阶段（R1/R3/R6）。

路由（人工拍板）与引擎（auto 模式代批，source=ai_review）共用——
两条路径写同一张台账、同一套快照语义，保证可审计可回放。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..db import Database, parse_json_or
from ..workspace import WorkspaceManager


class AdvanceError(Exception):
    """决策前置条件不满足（状态不对/阻塞问题未答全）。"""


@dataclass
class AnswerIn:
    id: str
    answer: str


@dataclass
class DefaultIn:
    id: str = "B-x"
    text: str = "默认假设"
    value: str = ""


@dataclass
class AdvanceResult:
    ok: bool
    next_stage: int
    snapshot_seq: int
    decisions_recorded: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)


def advance_stage(
    db: Database,
    ws: WorkspaceManager,
    project_id: int,
    stage: int,
    answers: list[AnswerIn],
    accepted_defaults: list[DefaultIn] | None = None,
    reason: str = "",
    source: str = "form",
    confirm_exemptions: bool = False,
) -> AdvanceResult:
    """提交阶段决策：校验状态 → 台账 → 快照 → 任务完结 → 解锁下一阶段。

    source: form/gallery/crit/rollback（人工）| ai_review（auto 代批）| defaults（B-x 默认）。
    confirm_exemptions: crit 决策存在豁免处置时的显式人工确认（豁免类必停人工的决策侧）。
    """
    from ..stages.registry import REGISTRY, crit_decision_items, gallery_items  # 延迟导入防环

    accepted_defaults = accepted_defaults or []
    if not answers:
        raise AdvanceError("决策内容为空（拍板不能是空操作）")
    card = REGISTRY.get(stage)
    if card is None:
        raise AdvanceError(f"阶段 {stage} 无任务卡")
    project = db.one("SELECT p.*, pr.name AS product_name FROM projects p JOIN products pr ON pr.id=p.product_id WHERE p.id=?", (project_id,))
    if project is None:
        raise AdvanceError(f"项目不存在：{project_id}")
    status_map = parse_json_or(project["stage_status"], {})
    if status_map.get(str(stage)) != "awaiting_decision":
        raise AdvanceError(f"阶段 {stage} 不在待决策状态（当前：{status_map.get(str(stage))}）")

    project_dir = ws.project_dir(project_id, project["product_id"])

    # ---- 硬校验（gate 的决策侧）：每类决策的完整性 ----
    if card.decision_type == "question_form":
        data = json.loads((project_dir / (card.decision_data_path or "")).read_text(encoding="utf-8"))
        required = {q["id"] for q in data.get("blocking", [])}
        missing = required - {a.id for a in answers}
        if missing:
            raise AdvanceError(f"阻塞问题未答全：{sorted(missing)}")
    elif card.decision_type == "gallery":
        items = gallery_items(card, project_dir)
        offered = {it["id"]: {o["label"] for o in it.get("options", [])} for it in items}
        missing = set(offered) - {a.id for a in answers}
        if missing:
            raise AdvanceError(f"变体选择未答全：{sorted(missing)}")
        for a in answers:
            labels = offered.get(a.id)
            if labels is None:
                raise AdvanceError(f"未知决策项：{a.id}")
            if a.answer not in labels and not a.answer.startswith("混搭："):
                raise AdvanceError(f"{a.id} 的选择非法（{'/'.join(sorted(labels))} 或 混搭：…）：{a.answer[:40]}")
    elif card.decision_type == "crit":
        data = json.loads((project_dir / (card.decision_data_path or "")).read_text(encoding="utf-8"))
        yellows, u_items = crit_decision_items(data)
        required = {f["id"] for f in yellows} | {u["id"] for u in u_items}
        missing = required - {a.id for a in answers}
        if missing:
            raise AdvanceError(f"crit 处置未答全：{sorted(missing)}")
        yellow_ids = {f["id"] for f in yellows}
        exemptions = []
        for a in answers:
            if a.id in yellow_ids and a.answer not in ("fix", "spec", "exempt"):
                raise AdvanceError(f"{a.id} 处置非法（fix/spec/exempt）：{a.answer[:40]}")
            if a.answer == "exempt":
                exemptions.append(a.id)
        if exemptions and not confirm_exemptions:
            raise AdvanceError(f"存在豁免处置（{sorted(exemptions)}）——豁免须显式人工确认（confirm_exemptions）")

    # 台账（R3）
    for a in answers:
        db.execute(
            "INSERT INTO decisions (project_id, stage, question_id, question, answer, source, reason) VALUES (?,?,?,?,?,?,?)",
            (project_id, stage, a.id, a.id, a.answer, source, reason or None),
        )
    for d in accepted_defaults:
        db.execute(
            "INSERT INTO decisions (project_id, stage, question_id, question, answer, source) VALUES (?,?,?,?,?,?)",
            (project_id, stage, d.id, d.text, d.value, "defaults"),
        )
    recorded = len(answers) + len(accepted_defaults)

    # 快照（R6）+ 任务完结 + 解锁下一阶段（R1）
    seq = len(db.query("SELECT id FROM snapshots WHERE project_id=?", (project_id,))) + 1
    snap_dir = ws.snapshot(project_dir, seq, stage)
    db.execute(
        "INSERT INTO snapshots (project_id, seq, stage, reason, dir) VALUES (?,?,?,?,?)",
        (project_id, seq, stage, reason or f"阶段 {stage} 确认（{source}）", str(snap_dir)),
    )
    db.execute(
        "UPDATE tasks SET state='completed', updated_at=datetime('now','localtime') WHERE project_id=? AND stage=? AND state='awaiting_decision'",
        (project_id, stage),
    )

    next_stage = stage + 1 if stage < 9 else stage
    status_map[str(stage)] = "done"
    if stage < 9:
        status_map[str(next_stage)] = "ready"
    db.execute(
        "UPDATE projects SET stage_status=?, current_stage=?, updated_at=datetime('now','localtime') WHERE id=?",
        (json.dumps(status_map, ensure_ascii=False), next_stage, project_id),
    )

    events = [
        {"type": "decision_recorded", "project_id": project_id, "stage": stage,
         "answers": [{"id": a.id, "answer": a.answer} for a in answers], "source": source},
        {"type": "snapshot_created", "project_id": project_id, "stage": stage, "seq": seq},
        {"type": "task_state", "project_id": project_id, "stage": stage, "state": "completed",
         "detail": f"阶段 {stage} 拍板（{source}）· 快照 #{seq} · 解锁阶段 {next_stage}"},
    ]
    return AdvanceResult(ok=True, next_stage=next_stage, snapshot_seq=seq, decisions_recorded=recorded, events=events)
