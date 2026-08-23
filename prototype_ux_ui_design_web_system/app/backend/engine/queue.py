"""任务引擎（产品心脏）：R7 全局串行队列 + 态机 + 双层 gate（L1 脚本 + L2 评审）+ 事件。

态机：queued → running → gate_running → review_running
                                                    ↓ (L1 不过 / 🔴>0) auto_redo ≤1（共享预算）→ failed_needs_human
                                                    ↓ (全过) awaiting_decision（decision_type=none 则 completed）
auto 模式且 human_decision=False（事实类阶段）：awaiting_decision 即由引擎代批（advance_stage,
source=ai_review）→ completed → 链式入队下一阶段。品味/答案/豁免类任何模式停人工。
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..db import Database
from ..settings import Settings
from ..stages.registry import REGISTRY, StageCard
from ..workspace import WorkspaceManager
from .advance import AdvanceError, AnswerIn, advance_stage
from .events import EventBus
from .reviewer import ReviewError, Reviewer
from .runner import MockRunner, Runner


class TaskError(Exception):
    pass


@dataclass
class Job:
    task_id: int
    project_id: int
    stage: int


class TaskEngine:
    def __init__(self, db: Database, ws: WorkspaceManager, settings: Settings, bus: EventBus, runner: Runner | None = None, reviewer: Reviewer | None = None) -> None:
        self.db = db
        self.ws = ws
        self.settings = settings
        self.bus = bus
        self.runner: Runner = runner or MockRunner()
        self.reviewer: Reviewer | None = reviewer  # None=L2 关闭（AI_REVIEWER=off）
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None
        self._current: Job | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_ident: int | None = None

    # ---------- 生命周期 ----------
    def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._loop_ident = threading.get_ident()
        self.bus.set_loop(self._loop)
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._work_loop())

    async def stop(self) -> None:
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 - 关停容错
                pass

    # ---------- 入队 ----------
    def enqueue_stage_task(self, project_id: int, stage: int, kind: str = "stage") -> int:
        card = REGISTRY.get(stage)
        if card is None:
            raise TaskError(f"阶段 {stage} 的任务卡尚未注册（M1 支持 1-2）")
        project = self.db.one("SELECT * FROM projects WHERE id=?", (project_id,))
        if project is None:
            raise TaskError(f"项目不存在：{project_id}")
        status = self._stage_status(project, stage)
        allowed = {"ready", "failed_needs_human"}
        if status not in allowed:
            raise TaskError(f"阶段 {stage} 当前状态 {status} 不可发起（允许：{'/'.join(sorted(allowed))}）")

        task_id = self.db.execute(
            "INSERT INTO tasks (project_id, stage, kind, state) VALUES (?,?,?,?)",
            (project_id, stage, kind, "queued"),
        )
        self._set_stage_status(project_id, stage, "running")
        job = Job(task_id, project_id, stage)
        # 同步端点跑在线程池：跨线程入队必须 call_soon_threadsafe，否则 worker 可能不被唤醒
        if self._loop is not None and threading.get_ident() != self._loop_ident:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, job)
        else:
            self._queue.put_nowait(job)
        self._emit("task_state", project_id=project_id, task_id=task_id, stage=stage, state="queued",
                   detail=f"阶段 {stage} · {card.name} 排队")
        return task_id

    # ---------- 工作循环（串行，R7） ----------
    async def _work_loop(self) -> None:
        while True:
            job = await self._queue.get()
            self._current = job
            try:
                await self._run_job(job)
            except Exception:  # noqa: BLE001 - 引擎不许死
                traceback.print_exc()
            finally:
                self._current = None
                self._queue.task_done()

    async def _run_job(self, job: Job) -> None:
        card = REGISTRY[job.stage]
        project = self.db.one("SELECT p.*, pr.name AS product_name FROM projects p JOIN products pr ON pr.id=p.product_id WHERE p.id=?", (job.project_id,))
        project_dir = self.ws.project_dir(job.project_id, project["product_id"])
        ctx = {
            "product_name": project["product_name"],
            "project_name": project["name"],
            "platform": project["platform"],
            "canvas": f"{project['canvas_w']}x{project['canvas_h']}",
        }
        started = time.monotonic()
        attempts_limit = 1 + self.settings.auto_redo_limit
        attempt = 0
        last_error: str = ""

        while attempt < attempts_limit:
            attempt += 1
            self._set_task(job.task_id, state="running" if attempt == 1 else "auto_redo", attempts=attempt)
            self._set_stage_status(job.project_id, job.stage, "running")
            self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                       state="running" if attempt == 1 else "auto_redo",
                       detail=f"阶段 {job.stage} · {card.name} · 第 {attempt}/{attempts_limit} 次执行")
            try:
                async def on_step(text: str) -> None:
                    self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage, step=text)

                async def on_artifact(path: str) -> None:
                    self._emit("artifact_increment", project_id=job.project_id, task_id=job.task_id, stage=job.stage, path=path)

                await self.runner.run(card.build_prompt(ctx), project_dir, card, on_step, on_artifact)
            except Exception as e:  # noqa: BLE001 - 运行失败统一进重试语义
                last_error = f"执行失败：{e}"
                self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                           step=last_error)
                continue  # 走重试

            # ---- L1 确定性 gate ----
            self._set_task(job.task_id, state="gate_running")
            self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                       state="gate_running", detail=f"L1 gate 校验：{card.name} 产物")
            gate = card.run_gate(self.ws, project_dir)
            self._set_task(job.task_id, gate_output="; ".join(gate.problems) if gate.problems else "PASS")
            self._emit("gate_result", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                       ok=gate.ok, problems=gate.problems)
            if not gate.ok:
                last_error = "gate 拦下：" + "；".join(gate.problems)
                self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage, step=last_error)
                continue

            # ---- L2 评审（判据卡 findings；verdict 引擎数出） ----
            if self.reviewer is not None and card.rubric_file is not None and card.criterion_ids:
                self._set_task(job.task_id, state="review_running")
                self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                           state="review_running", detail=f"L2 评审：{card.name} · 判据 {len(card.criterion_ids)} 条")
                try:
                    review = await self.reviewer.review(card, project_dir, self.ws)
                except ReviewError as e:
                    # 评审基础设施失败（进程/解析/覆盖不全）→ 不烧生成配额，直接转人工（失败无损）
                    self._fail(job, f"评审失败（非产物问题）：{e}", started)
                    return
                findings = review.get("findings", [])
                red = [f for f in findings if f.get("severity") == "red"]
                yellow = [f for f in findings if f.get("severity") == "yellow"]
                verdict = "pass" if not red else "redo"
                self.db.execute(
                    "INSERT INTO reviews (project_id, task_id, stage, attempt, verdict, findings, red_count, yellow_count) VALUES (?,?,?,?,?,?,?,?)",
                    (job.project_id, job.task_id, job.stage, attempt, verdict,
                     json.dumps(findings, ensure_ascii=False), len(red), len(yellow)),
                )
                self._set_task(job.task_id, review_output=json.dumps(findings, ensure_ascii=False))
                self._emit("review_result", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                           ok=verdict == "pass", red=len(red), yellow=len(yellow), findings=findings)
                if red:
                    last_error = "评审打回（🔴 %d）：" % len(red) + "；".join(
                        f"{f.get('criterion')}:{f.get('evidence', '')[:60]}" for f in red)
                    self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage, step=last_error)
                    continue  # 共享重试预算（防讨好评审器）
                if yellow:
                    self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                               step=f"评审带病通过：🟡 {len(yellow)} 条已记录在案（reviews 表）")

            # ---- 双层 gate 全过 ----
            cost = round(time.monotonic() - started, 1)
            final_state = "awaiting_decision" if card.decision_type != "none" else "completed"
            self._set_task(job.task_id, state=final_state, cost_s=cost)
            self._set_stage_status(job.project_id, job.stage, final_state)
            self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                       state=final_state, detail=f"双层 gate 通过（{cost}s）" + ("——等你拍板" if final_state == "awaiting_decision" else ""))

            # auto 代批：事实类阶段（human_decision=False）不停人工
            if final_state == "awaiting_decision" and project["run_mode"] == "auto" and not card.human_decision:
                self._auto_advance(job, card, project)
            return

        # 重试用尽 → 转人工（P2-3；失败不删任何已产出物）
        self._fail(job, last_error, started)

    def _fail(self, job: Job, message: str, started: float) -> None:
        cost = round(time.monotonic() - started, 1)
        self._set_task(job.task_id, state="failed_needs_human", error=message, cost_s=cost)
        self._set_stage_status(job.project_id, job.stage, "failed_needs_human")
        self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                   state="failed_needs_human", detail=message)

    def _auto_advance(self, job: Job, card: StageCard, project: dict[str, Any]) -> None:
        """auto 模式代批：台账(source=ai_review) + 快照 + 解锁 + 链式入队。"""
        try:
            result = advance_stage(
                self.db, self.ws, job.project_id, job.stage,
                answers=[AnswerIn(
                    id=f"stage-{job.stage}-auto",
                    answer="auto 放行：L1 gate 绿 + L2 评审 🔴=0（重试预算内）",
                )],
                accepted_defaults=[],
                reason="auto：双层 gate 放行",
                source="ai_review",
            )
        except AdvanceError as e:
            self._fail(job, f"auto 代批失败：{e}", time.monotonic())
            return
        for ev in result.events:
            self.bus.publish(ev.pop("type"), **ev)
        self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                   step=f"auto 代批：台账 #{result.decisions_recorded} 条 · 快照 #{result.snapshot_seq} · 阶段 {job.stage} 完成")
        # 链式入队下一阶段（未注册的阶段卡=停下等接入，发事件说明）
        if result.next_stage != job.stage:
            try:
                self.enqueue_stage_task(job.project_id, result.next_stage)
            except TaskError as e:
                self._emit("task_state", project_id=job.project_id, stage=result.next_stage, state="ready",
                           detail=f"阶段 {result.next_stage} 已解锁待接入：{e}")

    # ---------- 状态工具 ----------
    def _stage_status(self, project: dict[str, Any], stage: int) -> str:
        import json as _json
        try:
            m = _json.loads(project["stage_status"])
        except (ValueError, TypeError):
            m = {}
        return str(m.get(str(stage), "locked"))

    def _set_stage_status(self, project_id: int, stage: int, status: str) -> None:
        import json as _json
        project = self.db.one("SELECT stage_status FROM projects WHERE id=?", (project_id,))
        m: dict[str, str] = _json.loads(project["stage_status"] or "{}")
        m[str(stage)] = status
        self.db.execute("UPDATE projects SET stage_status=?, updated_at=datetime('now','localtime') WHERE id=?",
                        (_json.dumps(m, ensure_ascii=False), project_id))

    def _set_task(self, task_id: int, **fields: Any) -> None:
        cols = ", ".join(f"{k}=?" for k in fields)
        self.db.execute(f"UPDATE tasks SET {cols}, updated_at=datetime('now','localtime') WHERE id=?",
                        (*fields.values(), task_id))

    def _emit(self, type_: str, **payload: Any) -> None:
        self.bus.publish(type_, **payload)

    # ---------- 查询 ----------
    def current_job(self) -> dict[str, Any] | None:
        return {"task_id": self._current.task_id, "project_id": self._current.project_id, "stage": self._current.stage} if self._current else None
