"""任务引擎（产品心脏）：R7 全局串行队列 + 态机 + 双层 gate（L1 脚本 + L2 评审）+ 事件。

态机：queued → running → gate_running → review_running
                                                    ↓ (L1 不过 / 🔴>0) 共享重试 ≤2（总执行 ≤3）→ failed_needs_human
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

from ..db import Database, parse_json_or
from ..settings import Settings
from ..stages.registry import REGISTRY, StageCard, crit_decision_items, gallery_items
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
    revision_id: int | None = None  # 非空 = 增量任务（revision 工作区执行，阶段图读写 revisions）


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
            raise TaskError(f"阶段 {stage} 的任务卡尚未注册")
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
                   detail=f"阶段 {stage} · {card.name} 排队", design_mode=project["design_mode"])
        return task_id

    # ---------- 入队（revision 增量任务） ----------
    def enqueue_revision_stage_task(self, project_id: int, revision_id: int, stage: int) -> int:
        """增量任务：阶段图读 revisions.stage_status（不复用项目主流程的"已完成阶段不可再执行"限制）。"""
        card = REGISTRY.get(stage)
        if card is None:
            raise TaskError(f"阶段 {stage} 的任务卡尚未注册")
        revision = self.db.one("SELECT * FROM revisions WHERE id=? AND project_id=?", (revision_id, project_id))
        if revision is None:
            raise TaskError(f"revision 不存在：{revision_id}")
        if stage == 0:
            if revision["status"] != "analyzing":
                raise TaskError(f"revision 状态 {revision['status']} 不可发起影响分析（analyzing 才可）")
        else:
            if revision["status"] != "running":
                raise TaskError(f"revision 状态 {revision['status']} 不可发起增量阶段（先确认范围）")
        status = self._revision_stage_status(revision, stage)
        allowed = {"ready", "failed_needs_human"}
        if status not in allowed:
            raise TaskError(f"revision 阶段 {stage} 当前状态 {status} 不可发起（允许：{'/'.join(sorted(allowed))}）")

        task_id = self.db.execute(
            "INSERT INTO tasks (project_id, revision_id, stage, kind, state) VALUES (?,?,?,?,?)",
            (project_id, revision_id, stage, "stage", "queued"),
        )
        self._set_revision_stage_status(revision_id, stage, "running")
        job = Job(task_id, project_id, stage, revision_id=revision_id)
        if self._loop is not None and threading.get_ident() != self._loop_ident:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, job)
        else:
            self._queue.put_nowait(job)
        project = self.db.one("SELECT design_mode FROM projects WHERE id=?", (project_id,))
        self._emit("task_state", project_id=project_id, revision_id=revision_id, task_id=task_id, stage=stage,
                   state="queued", detail=f"revision R{revision['seq']} · 阶段 {stage} · {card.name} 排队",
                   design_mode=project["design_mode"] if project else "deliberate")
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
        revision = None
        if job.revision_id is not None:
            revision = self.db.one("SELECT * FROM revisions WHERE id=?", (job.revision_id,))
            if revision is None:
                self._emit("task_state", project_id=job.project_id, revision_id=job.revision_id,
                           task_id=job.task_id, stage=job.stage, state="failed_needs_human",
                           detail=f"revision 不存在：{job.revision_id}")
                return
            work_dir = self.ws.revision_dir(job.project_id, job.revision_id, project["product_id"])
        else:
            work_dir = self.ws.project_dir(job.project_id, project["product_id"])
        ctx = {
            "product_name": project["product_name"],
            "project_name": project["name"],
            "platform": project["platform"],
            "canvas_w": project["canvas_w"],
            "canvas_h": project["canvas_h"],
            "design_mode": project["design_mode"],
        }
        if revision is not None:
            base = self.db.one("SELECT seq, stage FROM snapshots WHERE id=?", (revision["base_snapshot_id"],))
            plan = (parse_json_or(revision["impact"], {}) or {}).get("plan") or {}
            ctx["revision"] = {
                "seq": revision["seq"],
                "title": revision["title"],
                "reason": revision["reason"],
                "base_seq": base["seq"] if base else "?",
                "change_levels": plan.get("change_levels") or [],
                "affected_pages": (plan.get("pages") or {}).get("modified", []) + (plan.get("pages") or {}).get("added", []),
                "regression_pages": plan.get("regression_pages") or [],
            }
        started = time.monotonic()
        attempts_limit = 1 + self.settings.auto_redo_limit
        attempt = 0
        last_error: str = ""

        while attempt < attempts_limit:
            attempt += 1
            self._set_task(job.task_id, state="running" if attempt == 1 else "auto_redo", attempts=attempt)
            self._job_set_stage_status(job, "running")
            self._emit("task_state", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                       state="running" if attempt == 1 else "auto_redo",
                       detail=f"{'revision R%d · ' % revision['seq'] if revision else ''}阶段 {job.stage} · {card.name} · 第 {attempt}/{attempts_limit} 次执行")
            try:
                async def on_step(text: str) -> None:
                    self._emit("task_step", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage, step=text)

                async def on_artifact(path: str) -> None:
                    self._emit("artifact_increment", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage, path=path)

                await self.runner.run(
                    card.build_prompt(ctx), work_dir, card, on_step, on_artifact,
                    canvas=(project["canvas_w"], project["canvas_h"]),
                    design_mode=project["design_mode"],
                    platform=project["platform"],
                )
            except Exception as e:  # noqa: BLE001 - 运行失败统一进重试语义
                last_error = f"执行失败：{e}"
                self._emit("task_step", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                           step=last_error)
                continue  # 走重试

            # ---- L1 确定性 gate ----
            self._set_task(job.task_id, state="gate_running")
            self._emit("task_state", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                       state="gate_running", detail=f"L1 gate 校验：{card.name} 产物")
            try:
                gate = card.run_gate(
                    self.ws, work_dir, (project["canvas_w"], project["canvas_h"]), project["design_mode"],
                    platform=project["platform"],
                )
            except Exception as e:  # noqa: BLE001 - gate 自身崩溃≠产物不合格，但按打回处理（预算内重试）
                last_error = f"gate 执行异常：{e}"
                self._emit("task_step", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage, step=last_error)
                continue
            self._set_task(job.task_id, gate_output="; ".join(gate.problems) if gate.problems else "PASS")
            self._emit("gate_result", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                       ok=gate.ok, problems=gate.problems)
            if not gate.ok:
                last_error = "gate 拦下：" + "；".join(gate.problems)
                self._emit("task_step", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage, step=last_error)
                continue

            # ---- L2 评审（判据卡 findings；verdict 引擎数出） ----
            if self.reviewer is not None and card.rubric_file is not None and card.criterion_ids:
                self._set_task(job.task_id, state="review_running")
                self._emit("task_state", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                           state="review_running", detail=f"L2 评审：{card.name} · 判据 {len(card.criterion_ids)} 条")
                try:
                    review = await self.reviewer.review(card, work_dir, self.ws, design_mode=project["design_mode"])
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
                self._emit("review_result", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                           ok=verdict == "pass", red=len(red), yellow=len(yellow), findings=findings)
                if red:
                    last_error = "评审打回（🔴 %d）：" % len(red) + "；".join(
                        f"{f.get('criterion')}:{f.get('evidence', '')[:60]}" for f in red)
                    self._emit("task_step", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage, step=last_error)
                    continue  # 共享重试预算（防讨好评审器）
                if yellow:
                    self._emit("task_step", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                               step=f"评审带病通过：🟡 {len(yellow)} 条已记录在案（reviews 表）")

            # ---- 双层 gate 全过 ----
            cost = round(time.monotonic() - started, 1)
            if revision is not None and card.decision_type == "impact":
                # 阶段 0：影响分析过双层 gate → revision 进入 impact_ready（范围由用户确认，不自动重跑）
                self._set_task(job.task_id, state="completed", cost_s=cost)
                self._set_revision_stage_status(revision["id"], 0, "done")
                self.db.execute(
                    "UPDATE revisions SET status='impact_ready', updated_at=datetime('now','localtime') WHERE id=?",
                    (revision["id"],),
                )
                self._emit("task_state", project_id=job.project_id, revision_id=revision["id"], task_id=job.task_id, stage=0,
                           state="completed", detail=f"影响分析通过双层 gate（{cost}s）——等你确认范围")
                return
            final_state = "awaiting_decision" if card.decision_type != "none" else "completed"
            self._set_task(job.task_id, state=final_state, cost_s=cost)
            self._job_set_stage_status(job, final_state)
            self._emit("task_state", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                       state=final_state, detail=f"双层 gate 通过（{cost}s）" + ("——等你拍板" if final_state == "awaiting_decision" else ""))

            # auto 代批：事实类不停人工；rapid+auto 额外覆盖 4/5（单候选默认采用）与 8（无豁免）。
            # revision 增量阶段一律停人工（增量变更必须显式拍板），不启用代批。
            if job.revision_id is None and final_state == "awaiting_decision" and project["run_mode"] == "auto" and self._may_auto_advance(card, project, work_dir):
                self._auto_advance(job, card, project, work_dir)
            return

        # 重试用尽 → 转人工（P2-3；失败不删任何已产出物）
        self._fail(job, last_error, started)

    def _fail(self, job: Job, message: str, started: float) -> None:
        cost = round(time.monotonic() - started, 1)
        self._set_task(job.task_id, state="failed_needs_human", error=message, cost_s=cost)
        self._job_set_stage_status(job, "failed_needs_human")
        self._emit("task_state", project_id=job.project_id, revision_id=job.revision_id, task_id=job.task_id, stage=job.stage,
                   state="failed_needs_human", detail=message)

    # rapid 模式（仅 auto 推进）的代批扩围：品味类 4/5 单候选默认采用；豁免类 8 无豁免才放行。
    # 答案类（1）与含豁免的 8 永远停人工；rapid+step 不改变 step 的每阶段确认语义。
    def _may_auto_advance(self, card: StageCard, project: dict[str, Any], project_dir: Path) -> bool:
        if not card.human_decision:
            return True
        if project["run_mode"] != "auto" or project["design_mode"] != "rapid":
            return False
        if card.stage in (4, 5):
            return True
        if card.stage == 8:
            return not self._stage8_has_exemptions(project_dir)
        return False

    @staticmethod
    def _stage8_has_exemptions(project_dir: Path) -> bool:
        jpath = project_dir / ".stage8-findings.json"
        try:
            data = json.loads(jpath.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return True  # 决策数据读不到 = 不允许自动放行（停人工）
        return any(f.get("proposed") == "exempt" for f in data.get("findings", []))

    def _auto_advance(self, job: Job, card: StageCard, project: dict[str, Any], project_dir: Path) -> None:
        """auto 推进代批：台账 + 快照 + 解锁 + 链式入队。source 按流程状态由服务端判定。"""
        rapid_default = (
            project["design_mode"] == "rapid" and project["run_mode"] == "auto" and card.stage in (4, 5, 8)
        )
        if rapid_default and card.stage in (4, 5):
            answers = [
                AnswerIn(id=it["id"], answer=it["options"][0]["label"])
                for it in gallery_items(card, project_dir)
                if it.get("options")
            ]
            reason = "rapid：单候选默认采用（布局模式/取舍/推导理由见产物帧下标注与 index）"
        elif rapid_default and card.stage == 8:
            data = json.loads((project_dir / (card.decision_data_path or "")).read_text(encoding="utf-8"))
            yellows, u_items = crit_decision_items(data)
            answers = [AnswerIn(f["id"], f.get("proposed") or "fix") for f in yellows] + [
                AnswerIn(u["id"], u["proposal"]) for u in u_items
            ]
            reason = "rapid：🟡 按建议处置、U-x 按倾向（无豁免项）"
        else:
            answers = [AnswerIn(
                id=f"stage-{job.stage}-auto",
                answer="auto 放行：L1 gate 绿 + L2 评审 🔴=0（重试预算内）",
            )]
            reason = "auto：双层 gate 放行"
        try:
            result = advance_stage(
                self.db, self.ws, job.project_id, job.stage,
                answers=answers,
                accepted_defaults=[],
                reason=reason,
                source="rapid_default" if rapid_default else "ai_review",
            )
        except AdvanceError as e:
            self._fail(job, f"auto 代批失败：{e}", time.monotonic())
            return
        for ev in result.events:
            self.bus.publish(ev.pop("type"), **ev)
        tail = " · 待最终验收（rapid）" if project["design_mode"] == "rapid" and job.stage == 9 else ""
        self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                   step=f"auto 代批：台账 #{result.decisions_recorded} 条 · 快照 #{result.snapshot_seq} · 阶段 {job.stage} 完成{tail}")
        # 链式入队下一阶段（未注册的阶段卡=停下等接入，发事件说明）
        if result.next_stage != job.stage:
            try:
                self.enqueue_stage_task(job.project_id, result.next_stage)
            except TaskError as e:
                self._emit("task_state", project_id=job.project_id, stage=result.next_stage, state="ready",
                           detail=f"阶段 {result.next_stage} 已解锁待接入：{e}")

    # ---------- 状态工具 ----------
    def _job_set_stage_status(self, job: Job, status: str) -> None:
        """阶段状态写入按 job 归属路由：项目主流程 → projects；增量 → revisions。"""
        if job.revision_id is not None:
            self._set_revision_stage_status(job.revision_id, job.stage, status)
        else:
            self._set_stage_status(job.project_id, job.stage, status)

    @staticmethod
    def _revision_stage_status(revision: dict[str, Any], stage: int) -> str:
        try:
            m = json.loads(revision["stage_status"] or "{}")
        except (ValueError, TypeError):
            m = {}
        return str(m.get(str(stage), "locked"))

    def _set_revision_stage_status(self, revision_id: int, stage: int, status: str) -> None:
        revision = self.db.one("SELECT stage_status FROM revisions WHERE id=?", (revision_id,))
        m: dict[str, str] = json.loads(revision["stage_status"] or "{}")
        m[str(stage)] = status
        self.db.execute("UPDATE revisions SET stage_status=?, updated_at=datetime('now','localtime') WHERE id=?",
                        (json.dumps(m, ensure_ascii=False), revision_id))

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
