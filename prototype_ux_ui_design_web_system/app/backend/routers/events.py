"""SSE 事件流（等待可离开：切走回来 replay 不丢上下文）+ 产物预览（同源 iframe）。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..deps import get_ws
from ..workspace import WorkspaceError, WorkspaceManager

router = APIRouter(prefix="/api")

MEDIA = {".html": "text/html", ".md": "text/plain; charset=utf-8", ".json": "application/json", ".txt": "text/plain; charset=utf-8"}


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    bus = request.app.state.bus
    sid, q, replay = bus.subscribe()

    async def gen():
        try:
            for e in replay:
                yield bus.sse_format(e)
            while True:
                try:
                    e = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield bus.sse_format(e)
        finally:
            bus.unsubscribe(sid)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/preview/{project_id}/{path:path}")
def preview(project_id: int, path: str, request: Request, ws: WorkspaceManager = Depends(get_ws)):
    db = request.app.state.db
    row = db.one("SELECT product_id FROM projects WHERE id=?", (project_id,))
    if row is None:
        raise HTTPException(404, "项目不存在")
    try:
        project_dir = ws.project_dir(project_id, row["product_id"])
        fpath = ws.resolve(project_dir, path)
    except WorkspaceError as e:
        raise HTTPException(404, str(e)) from e
    media = MEDIA.get(fpath.suffix.lower(), "application/octet-stream")
    return StreamingResponse(open(fpath, "rb"), media_type=media, headers={"Cache-Control": "no-cache"})
