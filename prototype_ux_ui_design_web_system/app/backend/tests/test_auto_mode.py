"""auto 模式：事实类阶段代批推进（台账 ai_review + 快照 + 链式解锁）；
答案类（阶段 1）与品味类任何模式必停人工；评审打回共享预算。"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from test_review_flow import ScriptedReviewer, RED


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as client:
        yield client, tmp_path


def _mk_project(client: TestClient, run_mode: str = "auto") -> int:
    r = client.post(
        "/api/products",
        json={"name": "P", "requirement_doc": "# 需求\n内容足够长。",
              "project": {"name": "手机App", "platform": "mobile_app", "run_mode": run_mode}},
    )
    return r.json()["projects"][0]["id"]


def _wait(client: TestClient, pid: int, stage: int, target: str, timeout_s: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        detail = client.get(f"/api/projects/{pid}").json()
        if detail["stage_status"].get(str(stage)) in (target, "failed_needs_human"):
            return detail
        time.sleep(0.1)
    raise AssertionError(f"阶段 {stage} 未到达 {target}（当前 {client.get(f'/api/projects/{pid}').json()['stage_status']}）")


def _finish_stage1_manually(client: TestClient, pid: int) -> None:
    """阶段 1 是答案类：auto 模式也停人工，人工答题解锁阶段 2。"""
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    _wait(client, pid, 1, "awaiting_decision")
    data = client.get(f"/api/projects/{pid}/decision/1").json()["data"]
    answers = [{"id": q["id"], "answer": q["options"][0]["label"]} for q in data["blocking"]]
    r = client.post(f"/api/projects/{pid}/stages/1/decision", json={"answers": answers})
    assert r.status_code == 200


def test_auto_mode_fact_stage_self_advances(env):
    client, tmp = env
    pid = _mk_project(client, run_mode="auto")
    _finish_stage1_manually(client, pid)

    client.post(f"/api/projects/{pid}/stages/2/tasks")
    detail = _wait(client, pid, 4, "awaiting_decision")
    # 事实类阶段 2、3：双层 gate 过 → 引擎代批 → done，链式入队直到阶段 4（品味类）停人工
    assert detail["stage_status"]["2"] == "done"
    assert detail["stage_status"]["3"] == "done"
    assert detail["stage_status"]["4"] == "awaiting_decision"
    assert detail["current_stage"] == 4

    # 代批写台账（source=ai_review）+ 快照；与人工拍板同一张表
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    ai_rows = [d for d in ledger["decisions"] if d["source"] == "ai_review"]
    assert {r["stage"] for r in ai_rows} == {2, 3}
    assert any(s["stage"] == 2 for s in ledger["snapshots"])
    # 快照目录落盘
    assert (tmp / "products" / "1" / "projects" / str(pid) / "snapshots" / "#2").is_dir()


def test_auto_mode_answer_stage_still_stops_human(env):
    client, _ = env
    pid = _mk_project(client, run_mode="auto")
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    detail = _wait(client, pid, 1, "awaiting_decision")
    assert detail["stage_status"]["1"] == "awaiting_decision"  # 答案类：auto 不代批


def test_auto_mode_review_red_shared_budget(env):
    client, _ = env
    pid = _mk_project(client, run_mode="auto")
    _finish_stage1_manually(client, pid)
    client.app.state.engine.reviewer = ScriptedReviewer([RED])  # 恒 🔴
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    detail = _wait(client, pid, 2, "done")  # target 兜底：failed 也会返回
    assert detail["stage_status"]["2"] == "failed_needs_human"
    task = client.get(f"/api/projects/{pid}/tasks/current").json()
    assert task["attempts"] == 3 and "评审打回" in (task["error"] or "")


def test_step_mode_unchanged_stops_for_stage2(env):
    client, _ = env
    pid = _mk_project(client, run_mode="step")
    _finish_stage1_manually(client, pid)
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    detail = _wait(client, pid, 2, "awaiting_decision")
    assert detail["stage_status"]["2"] == "awaiting_decision"  # step：事实类也停人工
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert not [d for d in ledger["decisions"] if d["source"] == "ai_review"]
