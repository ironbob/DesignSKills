"""L2 评审流：🔴 打回共享重试预算 → 转人工；🟢 过审记 reviews；覆盖不完整=打回。"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.engine.reviewer import ReviewError, parse_review_payload
from backend.stages.registry import REGISTRY


class ScriptedReviewer:
    """按调用次序返回预设 findings（最后一条之后复用）。"""

    def __init__(self, sequence: list[list[dict]]) -> None:
        self.sequence = sequence
        self.calls = 0

    async def review(self, card, project_dir, ws):
        findings = self.sequence[min(self.calls, len(self.sequence) - 1)]
        self.calls += 1
        return {"stage": card.stage, "findings": findings, "covered": sorted(card.criterion_ids), "not_applicable": []}


RED = [{"id": "F1-1", "criterion": "R1-1", "severity": "red", "evidence": "01 缺台账骨架", "suggestion": "补骨架"}]


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


def _wait_stage1(client: TestClient, pid: int, target: str, timeout_s: float = 15.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        detail = client.get(f"/api/projects/{pid}").json()
        if detail["stage_status"]["1"] in (target, "failed_needs_human"):
            return detail
        time.sleep(0.1)
    raise AssertionError(f"任务未到达 {target}")


def test_review_pass_records_row_and_advances_to_awaiting(env):
    client, _ = env
    pid = _mk_project(client)
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    detail = _wait_stage1(client, pid, "awaiting_decision")
    assert detail["stage_status"]["1"] == "awaiting_decision"

    task = client.get(f"/api/projects/{pid}/tasks/current").json()
    assert task["review_output"] == "[]"  # MockReviewer 全绿，findings 落任务行
    # reviews 表有 pass 记录（引擎数出 verdict，非评审器自报）
    db = client.app.state.db
    rows = db.query("SELECT * FROM reviews WHERE project_id=?", (pid,))
    assert len(rows) == 1 and rows[0]["verdict"] == "pass" and rows[0]["red_count"] == 0


def test_review_red_then_green_shared_budget(env):
    client, _ = env
    pid = _mk_project(client)
    client.app.state.engine.reviewer = ScriptedReviewer([RED, []])  # 首评 🔴，复审绿
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    detail = _wait_stage1(client, pid, "awaiting_decision")
    assert detail["stage_status"]["1"] == "awaiting_decision"

    task = client.get(f"/api/projects/{pid}/tasks/current").json()
    assert task["attempts"] == 2  # 共享预算：评审打回吃掉 auto_redo 一次
    db = client.app.state.db
    verdicts = [r["verdict"] for r in db.query("SELECT verdict FROM reviews WHERE project_id=? ORDER BY id", (pid,))]
    assert verdicts == ["redo", "pass"]


def test_review_red_persistent_fails_to_human(env):
    client, _ = env
    pid = _mk_project(client)
    client.app.state.engine.reviewer = ScriptedReviewer([RED])  # 恒 🔴
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    _wait_stage1(client, pid, "failed_needs_human")

    task = client.get(f"/api/projects/{pid}/tasks/current").json()
    assert task["attempts"] == 2  # 预算用尽（防讨好评审器循环）
    assert "评审打回" in (task["error"] or "")
    # 失败不锁阶段：可重试
    assert client.post(f"/api/projects/{pid}/stages/1/tasks").status_code == 201


def test_parse_review_rejects_incomplete_coverage():
    card = REGISTRY[1]
    assert card.criterion_ids, "判据卡应解析出判据号"
    with pytest.raises(ReviewError):
        parse_review_payload('{"findings": [], "covered": [], "not_applicable": []}', card)  # 覆盖不完整
    with pytest.raises(ReviewError):
        parse_review_payload("不是 JSON", card)
    ok = parse_review_payload(
        '{"findings": [{"id":"F1","criterion":"R1-2","severity":"yellow","evidence":"e","suggestion":"s"}], '
        '"covered": ['+ ",".join(f'"{c}"' for c in sorted(card.criterion_ids)) + '], "not_applicable": []}',
        card,
    )
    assert ok["findings"][0]["severity"] == "yellow"
