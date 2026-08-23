"""决策提交闭环：台账 + 快照 + 解锁（R1/R3/R6）。"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as client:
        yield client, tmp_path


def _to_awaiting(client: TestClient) -> int:
    r = client.post(
        "/api/products",
        json={"name": "P", "requirement_doc": "# 需求\n内容", "project": {"name": "手机App", "platform": "mobile_app"}},
    )
    pid = r.json()["projects"][0]["id"]
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        d = client.get(f"/api/projects/{pid}").json()
        if d["stage_status"]["1"] == "awaiting_decision":
            return pid
        time.sleep(0.1)
    raise AssertionError("未到待决策态")


def test_decision_full_loop(env):
    client, tmp = env
    pid = _to_awaiting(client)

    # 不全答 → 422（零裸答与零裸问对称）
    data = client.get(f"/api/projects/{pid}/decision/1").json()["data"]
    first_id = data["blocking"][0]["id"]
    r = client.post(f"/api/projects/{pid}/stages/1/decision", json={"answers": [{"id": first_id, "answer": "x"}]})
    assert r.status_code == 422

    # 全答 → 台账+快照+解锁
    answers = [{"id": q["id"], "answer": q["options"][0]["label"]} for q in data["blocking"]]
    r = client.post(
        f"/api/projects/{pid}/stages/1/decision",
        json={"answers": answers, "accepted_defaults": data["defaults"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["next_stage"] == 2 and body["snapshot_seq"] == 1

    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["stage_status"]["1"] == "done"
    assert detail["stage_status"]["2"] == "ready"
    assert detail["current_stage"] == 2

    # 台账与快照落盘
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert len(ledger["decisions"]) == len(data["blocking"]) + len(data["defaults"])
    assert ledger["snapshots"][0]["seq"] == 1
    assert (tmp / "products" / "1" / "projects" / str(pid) / "snapshots" / "#1").is_dir()

    # 任务完结
    task = client.get(f"/api/projects/{pid}/tasks/current").json()
    assert task["state"] == "completed"

    # 阶段 2 已可发起
    assert client.post(f"/api/projects/{pid}/stages/2/tasks").status_code == 201


def test_decision_rejects_when_not_awaiting(env):
    client, _ = env
    r = client.post(
        "/api/products",
        json={"name": "P2", "requirement_doc": "内容", "project": {"name": "W", "platform": "web"}},
    )
    pid = r.json()["projects"][0]["id"]
    resp = client.post(f"/api/projects/{pid}/stages/1/decision", json={"answers": []})
    assert resp.status_code == 409
