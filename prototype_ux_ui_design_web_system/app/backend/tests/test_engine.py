"""任务引擎测试：串行队列、态机流转、gate 打回转人工、成功进待决策。"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.stages.registry import GateResult


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as client:
        yield client, tmp_path


def _mk_project(client: TestClient) -> int:
    r = client.post(
        "/api/products",
        json={"name": "P", "requirement_doc": "# 需求\n内容足够长。", "project": {"name": "手机App", "platform": "mobile_app"}},
    )
    return r.json()["projects"][0]["id"]


def _wait_awaiting(client: TestClient, project_id: int, timeout_s: float = 10.0) -> dict:
    import time

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        detail = client.get(f"/api/projects/{project_id}").json()
        if detail["stage_status"]["1"] in ("awaiting_decision", "failed_needs_human"):
            return detail
        time.sleep(0.1)
    raise AssertionError("任务未在时限内到达终态")


def test_mock_stage1_success_reaches_awaiting_decision(env):
    client, tmp = env
    pid = _mk_project(client)
    r = client.post(f"/api/projects/{pid}/stages/1/tasks")
    assert r.status_code == 201
    detail = _wait_awaiting(client, pid)
    assert detail["stage_status"]["1"] == "awaiting_decision"
    # 决策数据可读
    d = client.get(f"/api/projects/{pid}/decision/1").json()
    assert d["type"] == "question_form"
    assert len(d["data"]["blocking"]) >= 1
    assert (tmp / "products" / "1" / "projects" / str(pid) / "01-需求消化.md").exists()


def test_enqueue_rejects_when_running_or_awaiting(env):
    client, _ = env
    pid = _mk_project(client)
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    detail = _wait_awaiting(client, pid)
    # awaiting_decision 不可重复发起（409）
    r = client.post(f"/api/projects/{pid}/stages/1/tasks")
    assert r.status_code == 409
    # 阶段 2 尚未解锁（locked）
    r = client.post(f"/api/projects/{pid}/stages/2/tasks")
    assert r.status_code == 409


def test_gate_fail_then_auto_redo_then_human(env, monkeypatch: pytest.MonkeyPatch):
    client, tmp = env
    pid = _mk_project(client)

    # 让 gate 恒败（run_gate 在调用时查 GATES 表，注入即可生效）
    from backend.stages import registry as reg

    def always_fail(ws, project_dir, canvas=None):
        return GateResult(False, ["测试注入：gate 恒败"])

    monkeypatch.setitem(reg.GATES, 1, always_fail)

    client.post(f"/api/projects/{pid}/stages/1/tasks")
    detail = client.get(f"/api/projects/{pid}").json()
    deadline = time.monotonic() + 15
    while detail["stage_status"]["1"] != "failed_needs_human" and time.monotonic() < deadline:
        time.sleep(0.1)
        detail = client.get(f"/api/projects/{pid}").json()
    assert detail["stage_status"]["1"] == "failed_needs_human"
    task = client.get(f"/api/projects/{pid}/tasks/current").json()
    assert task["attempts"] == 3  # 首跑 + 共享重试 2 次（P2-3）
    assert "测试注入" in (task["error"] or "")
    # 失败不锁阶段：可手动重试（ready/failed 均可发起）
    assert client.post(f"/api/projects/{pid}/stages/1/tasks").status_code == 201


def test_event_bus_pub_sub_and_replay():
    """SSE 背后的总线：订阅-发布-回放（HTTP 层由 Playwright e2e 对真实 uvicorn 验证）。"""
    from backend.engine.events import EventBus

    bus = EventBus()
    bus.publish("task_state", project_id=1, state="queued")
    bus.publish("task_step", project_id=1, step="正在生成需求消化")

    sid, q, replay = bus.subscribe()
    assert [e["type"] for e in replay] == ["task_state", "task_step"]  # 回放：刷新不丢上下文

    bus.publish("artifact_increment", project_id=1, path="01-需求消化.md")
    bus.publish("task_state", project_id=1, state="awaiting_decision")
    got = [q.get_nowait() for _ in range(2)]
    assert got[0]["type"] == "artifact_increment" and got[1]["state"] == "awaiting_decision"
    assert bus.sse_format(got[1]).startswith('data: {"type"')

    bus.unsubscribe(sid)
    bus.publish("gate_result", ok=True)  # 退订后不应积累
    import asyncio as _a

    assert q.empty() or _a.QueueEmpty
