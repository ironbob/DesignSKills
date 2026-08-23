"""SSE 事件总线：引擎 → 前端单向流（09-spec：等待可离开——事件驱动，无轮询）。

线程模型：publish 可能来自事件循环（引擎 worker）或线程池（同步端点入队）；
跨线程投递一律 call_soon_threadsafe，保证等待中的 SSE 订阅者被立即唤醒。
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import deque
from typing import Any

REPLAY_LIMIT = 200  # 新订阅者补看最近事件（刷新页面不丢上下文）


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[int, asyncio.Queue[dict[str, Any]]] = {}
        self._next = 0
        self._ring: deque[dict[str, Any]] = deque(maxlen=REPLAY_LIMIT)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_ident: int | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """在事件循环线程内调用（engine.start）：记录 loop 与其线程 ident。"""
        self._loop = loop
        self._loop_ident = threading.get_ident()

    def publish(self, type_: str, **payload: Any) -> None:
        event = {"type": type_, "ts": round(time.time(), 3), **payload}
        loop = self._loop
        if loop is not None and threading.get_ident() != self._loop_ident:
            loop.call_soon_threadsafe(self._dispatch, event)
        else:
            self._dispatch(event)

    def _dispatch(self, event: dict[str, Any]) -> None:
        self._ring.append(event)
        for q in list(self._subs.values()):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:  # 订阅者落后太多则丢弃其积压旧值
                pass

    def subscribe(self) -> tuple[int, asyncio.Queue[dict[str, Any]], list[dict[str, Any]]]:
        self._next += 1
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._subs[self._next] = q
        return self._next, q, list(self._ring)

    def unsubscribe(self, sid: int) -> None:
        self._subs.pop(sid, None)

    def sse_format(self, event: dict[str, Any]) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

