"""FastAPI 依赖：db / workspace 从 app.state 取（tests 里可 override）。"""

from __future__ import annotations

from fastapi import Depends, Request

from .db import Database
from .workspace import WorkspaceManager


def get_db(request: Request) -> Database:
    return request.app.state.db  # type: ignore[no-any-return]


def get_ws(request: Request) -> WorkspaceManager:
    return request.app.state.ws  # type: ignore[no-any-return]


DbDep = Depends(get_db)
WsDep = Depends(get_ws)
