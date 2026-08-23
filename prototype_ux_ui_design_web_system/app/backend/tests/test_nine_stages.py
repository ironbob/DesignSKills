"""九阶段 mock 全链路 E2E。

覆盖：step 模式九阶段全停人工；auto 模式 2/3/6/7/9 代批推进 + 1/4/5/8 必停；
L1 打回吃共享重试预算后通过；crit 豁免须显式确认；快照/台账/reviews 可审计；
最终契约三件套（09-spec + 06-tokens + 07-hifi）落盘。

真实 claude runner 与 calibrate 未在测试内运行（不烧配额、不伪造结果）。
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.stages.registry as registry
from backend.engine.runner import MockRunner

from test_review_flow import RED, ScriptedReviewer

YELLOW = [{"id": "F9-1", "criterion": "R2-5", "severity": "yellow", "evidence": "支线挂载标注弱", "suggestion": "补虚线标注"}]


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as client:
        client.app.state.engine.runner = MockRunner(delay_s=0.02)  # 全链路九阶段，提速
        yield client, tmp_path


def _mk_project(client: TestClient, run_mode: str = "step") -> int:
    r = client.post(
        "/api/products",
        json={"name": "P", "requirement_doc": "# 需求\n背单词练习 App，每日任务与错词强化。",
              "project": {"name": "手机App", "platform": "mobile_app", "run_mode": run_mode}},
    )
    return r.json()["projects"][0]["id"]


def _wait(client: TestClient, pid: int, stage: int, target: str, timeout_s: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        detail = client.get(f"/api/projects/{pid}").json()
        if detail["stage_status"].get(str(stage)) in (target, "failed_needs_human"):
            return detail
        time.sleep(0.1)
    raise AssertionError(f"阶段 {stage} 未到达 {target}（当前 {client.get(f'/api/projects/{pid}').json()['stage_status']}）")


def _decide(client: TestClient, pid: int, stage: int, **overrides) -> object:
    """按决策类型提交拍板：问题单逐题 / gallery 逐项选择 / crit 处置（豁免须确认）/ confirm。"""
    d = client.get(f"/api/projects/{pid}/decision/{stage}").json()
    if d["type"] == "question_form":
        payload = {
            "answers": [{"id": q["id"], "answer": q["options"][0]["label"]} for q in d["data"]["blocking"]],
            "accepted_defaults": d["data"].get("defaults", []),
        }
    elif d["type"] == "gallery":
        payload = {"answers": [{"id": it["id"], "answer": it["options"][0]["label"]} for it in d["data"]["items"]]}
    elif d["type"] == "crit":
        answers = [{"id": f["id"], "answer": overrides.get("yellow_disposition", f.get("proposed") or "fix")}
                   for f in d["data"]["yellows"]]
        answers += [{"id": u["id"], "answer": u["proposal"]} for u in d["data"]["u_items"]]
        payload = {"answers": answers, "confirm_exemptions": any(a["answer"] == "exempt" for a in answers)}
    else:  # confirm
        payload = {"answers": [{"id": f"stage-{stage}-confirm", "answer": "确认"}]}
    r = client.post(f"/api/projects/{pid}/stages/{stage}/decision", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _stage1_manual(client: TestClient, pid: int) -> None:
    """阶段 1（答案类）：任何模式都停人工，答题解锁阶段 2。"""
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    _wait(client, pid, 1, "awaiting_decision")
    _decide(client, pid, 1)


def _task_attempts(client: TestClient, pid: int, stage: int) -> int:
    row = client.app.state.db.query(
        "SELECT attempts FROM tasks WHERE project_id=? AND stage=? ORDER BY id DESC LIMIT 1",
        (pid, stage),
    )
    return row[0]["attempts"]


def _ws_dir(tmp: Path, pid: int) -> Path:
    return tmp / "products" / "1" / "projects" / str(pid)


def test_step_mode_full_nine_stages_to_spec(env):
    client, tmp = env
    pid = _mk_project(client, run_mode="step")
    for stage in range(1, 10):
        client.post(f"/api/projects/{pid}/stages/{stage}/tasks")
        _wait(client, pid, stage, "awaiting_decision")
        _decide(client, pid, stage)

    detail = client.get(f"/api/projects/{pid}").json()
    assert all(detail["stage_status"][str(s)] == "done" for s in range(1, 10))
    assert detail["current_stage"] == 9

    # 最终规格导出：契约三件套落盘
    wdir = _ws_dir(tmp, pid)
    assert (wdir / "09-spec.md").exists()
    assert (wdir / "06-tokens.json").exists()
    assert any((wdir / "07-hifi").glob("S*.html"))

    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert {d["stage"] for d in ledger["decisions"]} == set(range(1, 10))   # 每阶段有拍板
    assert len(ledger["snapshots"]) == 9                                     # 每阶段有快照
    assert len(ledger["reviews"]) == 9                                       # 每阶段有 L2 评审记录
    assert not [d for d in ledger["decisions"] if d["source"] == "ai_review"]  # step 无代批


def test_auto_mode_full_nine_stages_with_human_points(env):
    client, tmp = env
    pid = _mk_project(client, run_mode="auto")

    # 阶段 1（答案类）：auto 也停人工
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    _wait(client, pid, 1, "awaiting_decision")
    _decide(client, pid, 1)
    # 阶段 2、3（事实类）：auto 链式代批，直到阶段 4（品味类）停人工
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    _wait(client, pid, 4, "awaiting_decision")
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["stage_status"]["2"] == "done" and detail["stage_status"]["3"] == "done"
    assert detail["stage_status"]["4"] == "awaiting_decision"
    _decide(client, pid, 4)  # gallery：逐屏挑变体

    client.post(f"/api/projects/{pid}/stages/5/tasks")  # 品味类：发起后停人工
    _wait(client, pid, 5, "awaiting_decision")
    _decide(client, pid, 5)

    client.post(f"/api/projects/{pid}/stages/6/tasks")  # 6、7 事实类链式代批 → 8 豁免类停
    _wait(client, pid, 8, "awaiting_decision")
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["stage_status"]["6"] == "done" and detail["stage_status"]["7"] == "done"

    # crit：豁免处置必须显式确认，否则 422
    d = client.get(f"/api/projects/{pid}/decision/8").json()
    assert d["type"] == "crit" and d["data"]["yellows"]
    exempt_payload = {"answers": [{"id": f["id"], "answer": "exempt"} for f in d["data"]["yellows"]]
                      + [{"id": u["id"], "answer": u["proposal"]} for u in d["data"]["u_items"]]}
    r = client.post(f"/api/projects/{pid}/stages/8/decision", json=exempt_payload)
    assert r.status_code == 422 and "豁免" in r.json()["detail"]
    r = client.post(f"/api/projects/{pid}/stages/8/decision",
                    json={**exempt_payload, "confirm_exemptions": True})
    assert r.status_code == 200, r.text

    client.post(f"/api/projects/{pid}/stages/9/tasks")  # 9 事实类：auto 直接完成
    _wait(client, pid, 9, "done")

    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    ai_stages = {d["stage"] for d in ledger["decisions"] if d["source"] == "ai_review"}
    assert ai_stages == {2, 3, 6, 7, 9}  # 仅事实类代批
    human_stages = {d["stage"] for d in ledger["decisions"] if d["source"] == "form"}
    assert human_stages == {1, 4, 5, 8}
    assert (_ws_dir(tmp, pid) / "09-spec.md").exists()
    assert len(ledger["snapshots"]) == 9


def test_l1_rejection_uses_shared_budget_then_passes(env, monkeypatch):
    client, _ = env
    pid = _mk_project(client, run_mode="auto")
    _stage1_manual(client, pid)  # 阶段 2 auto 代批，链式入队 3

    orig = registry.GATES[3]
    calls = {"n": 0}

    def flaky(ws, project_dir, canvas=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return registry.GateResult(False, ["注入：第一次 L1 拦下（预算测试）"])
        return orig(ws, project_dir, canvas)

    monkeypatch.setitem(registry.GATES, 3, flaky)
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    detail = _wait(client, pid, 4, "awaiting_decision")  # 3 被拦一次重做过 → 链到阶段 4 停人工
    assert detail["stage_status"]["3"] == "done"
    assert _task_attempts(client, pid, 3) == 2  # L1 打回吃掉一次共享重试


def test_l2_red_exhausts_shared_budget_to_human(env):
    client, _ = env
    pid = _mk_project(client, run_mode="auto")
    _stage1_manual(client, pid)
    client.app.state.engine.reviewer = ScriptedReviewer([RED])  # 恒 🔴
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    detail = _wait(client, pid, 2, "done")
    assert detail["stage_status"]["2"] == "failed_needs_human"
    assert _task_attempts(client, pid, 2) == 3  # 初次 + 2 次共享重试用尽 → 转人工（失败无损）
    # 3 次评审全部落 reviews 表（可审计可回放）
    reviews = client.get(f"/api/projects/{pid}/ledger").json()["reviews"]
    stage2 = [r for r in reviews if r["stage"] == 2]
    assert len(stage2) == 3 and all(r["verdict"] == "redo" for r in stage2)


def test_l2_yellow_recorded_but_passes(env):
    client, _ = env
    pid = _mk_project(client, run_mode="auto")
    _stage1_manual(client, pid)
    client.app.state.engine.reviewer = ScriptedReviewer([YELLOW])  # 恒 🟡
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    _wait(client, pid, 4, "awaiting_decision")  # 🟡 不阻断：阶段 2 带病通过并代批，链到 4
    reviews = client.get(f"/api/projects/{pid}/ledger").json()["reviews"]
    stage2 = [r for r in reviews if r["stage"] == 2]
    assert stage2 and stage2[0]["verdict"] == "pass" and stage2[0]["yellow_count"] == 1
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert any(d["stage"] == 2 and d["source"] == "ai_review" for d in ledger["decisions"])
