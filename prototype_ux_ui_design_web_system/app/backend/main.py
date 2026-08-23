"""AI 设计工作台 backend 入口。

产品契约：prototype_ux_ui_design_web_system/design/09-spec.md
- 对象两级：产品（共享需求文档）→ 项目（锁端：mobile_app/desktop_app/web）
- 九阶段推进：任务→gate→决策点→台账+快照→解锁
- R7 任务全局串行；gate=任务完成条件；失败单屏级不锁阶段
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import Database
from .engine.claude_runner import ClaudeRunner
from .engine.events import EventBus
from .engine.queue import TaskEngine
from .engine.reviewer import ClaudeReviewer, MockReviewer, Reviewer
from .engine.runner import MockRunner, Runner
from .routers import events, products, workbench
from .settings import get_settings
from .workspace import WorkspaceManager


def _pick_runner(s) -> Runner:
    if s.runner == "claude":
        return ClaudeRunner(s)
    return MockRunner()


def _pick_reviewer(s) -> Reviewer | None:
    if s.reviewer == "claude":
        return ClaudeReviewer(s)
    if s.reviewer == "mock":
        return MockReviewer()
    return None  # AI_REVIEWER=off：跳过 L2，只跑 L1


def create_app() -> FastAPI:
    s = get_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    db = Database(s.data_dir / "workbench.db")
    ws = WorkspaceManager(s.data_dir)
    bus = EventBus()
    runner = _pick_runner(s)  # AI_RUNNER=claude 真跑；默认 mock 不烧配额
    reviewer = _pick_reviewer(s)  # AI_REVIEWER 独立配置；默认跟随 runner

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = TaskEngine(db, ws, s, bus, runner, reviewer)
        app.state.engine = engine
        engine.start()
        yield
        await engine.stop()

    app = FastAPI(title="AI 设计工作台", lifespan=lifespan)
    app.state.db = db
    app.state.ws = ws
    app.state.bus = bus
    app.state.settings = s

    app.include_router(products.router)
    app.include_router(workbench.router)
    app.include_router(events.router)

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True, "service": "design-workbench", "runner": s.runner, "reviewer": s.reviewer, "data_dir": str(s.data_dir)}

    return app


app = create_app()
