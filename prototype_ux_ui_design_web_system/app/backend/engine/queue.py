"""任务引擎（产品心脏）：R7 全局串行队列 + 态机 + gate + 事件。

态机：queued → running → gate_running → (不过) auto_redo ≤1 → failed_needs_human
                                                    ↘ (过) awaiting_decision（decision_type=none 则 completed）
"""

from __future__ import annotations

import asyncio
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
from .events import EventBus
from .runner import MockRunner, Runner


class TaskError(Exception):
    pass


@dataclass
class Job:
    task_id: int
    project_id: int
    stage: int


class TaskEngine:
    def __init__(self, db: Database, ws: WorkspaceManager, settings: Settings, bus: EventBus, runner: Runner | None = None) -> None:
        self.db = db
        self.ws = ws
        self.settings = settings
        self.bus = bus
        self.runner: Runner = runner or MockRunner()
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
            except Exception as e:  # noqa: BLE001 - 运行失败统一进 gate 重试语义
                last_error = f"执行失败：{e}"
                self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                           step=last_error)
                continue  # 走重试

            self._set_task(job.task_id, state="gate_running")
            self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                       state="gate_running", detail=f"gate 校验：{card.name} 产物")
            gate = card.run_gate(self.ws, project_dir)
            self._set_task(job.task_id, gate_output="; ".join(gate.problems) if gate.problems else "PASS")
            self._emit("gate_result", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                       ok=gate.ok, problems=gate.problems)
            if gate.ok:
                cost = round(time.monotonic() - started, 1)
                final_state = "awaiting_decision" if card.decision_type != "none" else "completed"
                self._set_task(job.task_id, state=final_state, cost_s=cost)
                self._set_stage_status(job.project_id, job.stage, final_state)
                self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                           state=final_state, detail=f"gate 通过（{cost}s）" + ("——等你拍板" if final_state == "awaiting_decision" else ""))
                return
            last_error = "gate 拦下：" + "；".join(gate.problems)
            self._emit("task_step", project_id=job.project_id, task_id=job.task_id, stage=job.stage, step=last_error)

        # 重试用尽 → 转人工（P2-3；失败不删任何已产出物）
        cost = round(time.monotonic() - started, 1)
        self._set_task(job.task_id, state="failed_needs_human", error=last_error, cost_s=cost)
        self._set_stage_status(job.project_id, job.stage, "failed_needs_human")
        self._emit("task_state", project_id=job.project_id, task_id=job.task_id, stage=job.stage,
                   state="failed_needs_human", detail=last_error)

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
