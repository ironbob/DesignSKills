"""rapid 设计模式验收。

design_mode（deliberate/rapid）与 run_mode（step/auto）正交；rapid 只减候选数与非必要确认，
质量 gate（L1 全项 / L2 fresh context+完整覆盖+🔴 阻断）不减；默认决策 source=rapid_default
由服务端写入、台账可追溯；阶段 9 后进一次最终验收（awaiting_acceptance → done）。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.engine.queue import TaskEngine
from backend.engine.reviewer import ClaudeReviewer
from backend.engine.runner import MockRunner
from backend.settings import Settings

from test_review_flow import RED, ScriptedReviewer


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as client:
        client.app.state.engine.runner = MockRunner(delay_s=0.02)
        yield client, tmp_path


def _mk_project(client: TestClient, run_mode: str = "auto", design_mode: str | None = None) -> int:
    project: dict = {"name": "手机App", "platform": "mobile_app", "run_mode": run_mode}
    if design_mode is not None:
        project["design_mode"] = design_mode
    r = client.post(
        "/api/products",
        json={"name": "P", "requirement_doc": "# 需求\n背单词练习 App，每日任务与错词强化。", "project": project},
    )
    return r.json()["projects"][0]["id"]


def _wait(client: TestClient, pid: int, target_map: dict[int, str], timeout_s: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        detail = client.get(f"/api/projects/{pid}").json()
        if all(detail["stage_status"].get(str(s)) == st for s, st in target_map.items()):
            return detail
        if any(detail["stage_status"].get(str(s)) == "failed_needs_human" for s in target_map):
            return detail
        time.sleep(0.1)
    raise AssertionError(f"未到达 {target_map}（当前 {client.get(f'/api/projects/{pid}').json()['stage_status']}）")


def _stage1_manual(client: TestClient, pid: int, send_defaults: bool = True) -> dict:
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    _wait(client, pid, {1: "awaiting_decision"})
    data = client.get(f"/api/projects/{pid}/decision/1").json()["data"]
    payload = {"answers": [{"id": q["id"], "answer": q["options"][0]["label"]} for q in data["blocking"]]}
    if send_defaults:
        payload["accepted_defaults"] = data.get("defaults", [])
    r = client.post(f"/api/projects/{pid}/stages/1/decision", json=payload)
    assert r.status_code == 200, r.text
    return data


def _ws_dir(tmp: Path, pid: int) -> Path:
    return tmp / "products" / "1" / "projects" / str(pid)


# ---- 1. 既有项目默认 deliberate；step/auto 行为不回归 ----

def test_existing_project_defaults_deliberate_and_step_flow_intact(env):
    client, _ = env
    pid = _mk_project(client, run_mode="step")  # 不传 design_mode
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["design_mode"] == "deliberate"

    _stage1_manual(client, pid)
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    _wait(client, pid, {2: "awaiting_decision"})  # step：事实类仍停人工
    r = client.post(f"/api/projects/{pid}/stages/2/decision",
                    json={"answers": [{"id": "stage-2-confirm", "answer": "确认"}]})
    assert r.status_code == 200 and r.json()["next_stage"] == 3
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert ledger["design_mode"] == "deliberate"
    assert not [d for d in ledger["decisions"] if d["source"] == "rapid_default"]


# ---- 2. rapid + step：阶段 1 仅阻塞问题打断；阶段 2 确认可继续快速执行 ----

def test_rapid_step_blocking_only_and_stage2_quick_continue(env):
    client, _ = env
    pid = _mk_project(client, run_mode="step", design_mode="rapid")
    data = _stage1_manual(client, pid, send_defaults=False)  # 客户端不传默认——服务端自动采用

    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    rd = [d for d in ledger["decisions"] if d["source"] == "rapid_default"]
    assert rd and all(d["stage"] == 1 for d in rd)          # 非阻塞默认已自动入台账
    assert {d["question_id"] for d in rd} >= {"B-1"} if data.get("defaults") else True
    assert all(d["reason"] for d in rd)                       # 默认决策带理由

    client.post(f"/api/projects/{pid}/stages/2/tasks")
    _wait(client, pid, {2: "awaiting_decision"})              # step 语义保留：确认点在
    d = client.get(f"/api/projects/{pid}/decision/2").json()
    assert d["type"] == "confirm"
    r = client.post(f"/api/projects/{pid}/stages/2/decision",
                    json={"answers": [{"id": "stage-2-confirm", "answer": "继续快速执行"}]})
    assert r.status_code == 200                               # 低摩擦继续（一次确认）
    detail = _wait(client, pid, {3: "ready"})
    assert detail["stage_status"]["3"] == "ready"


# ---- 3/5/8. rapid + auto 全链路：单候选 + rapid_default 台账 + 最终验收 ----

def test_rapid_auto_full_flow_single_candidate_to_final_acceptance(env):
    client, tmp = env
    pid = _mk_project(client, run_mode="auto", design_mode="rapid")

    _stage1_manual(client, pid, send_defaults=False)
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    # 2/3 代批 → 4/5 单候选 rapid_default 代批 → 6/7 代批 → 8 无豁免代批 → 9 待最终验收
    detail = _wait(client, pid, {9: "awaiting_acceptance"})
    assert detail["stage_status"]["9"] == "awaiting_acceptance"      # 不是 done：必须一次最终验收
    assert all(detail["stage_status"][str(s)] == "done" for s in range(1, 9))
    assert detail["design_mode"] == "rapid"

    wdir = _ws_dir(tmp, pid)
    wires = sorted(p.name for p in (wdir / "04-wireframes").glob("S*-v*.html"))
    assert all(n.endswith("-v1.html") for n in wires) and wires      # 只有一套结构方案
    tiles = sorted(p.name for p in (wdir / "05-style-tiles").glob("tile-*.html"))
    assert tiles == ["tile-a.html"]                                  # 只有一个默认方向

    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    rd = [d for d in ledger["decisions"] if d["source"] == "rapid_default"]
    rd_stages = {d["stage"] for d in rd}
    assert rd_stages == {1, 4, 5, 8}                                 # 默认假设+4/5 单候选+8 处置
    assert all(d.get("reason") for d in rd if d["stage"] in (4, 5, 8))  # 台账有理由可追溯
    human = {d["stage"] for d in ledger["decisions"] if d["source"] == "form"}
    assert human == {1}                                              # 全流程只打断阶段 1（阻塞问题）
    assert len(ledger["reviews"]) == 9                               # L2 九阶段全跑（gate 不减）

    acc = client.get(f"/api/projects/{pid}/acceptance").json()
    assert acc["design_mode"] == "rapid" and acc["spec"] == "09-spec.md"
    assert any(f["path"] == "09-spec.md" for f in acc["contract_files"])
    assert any(f["path"] == "06-tokens.json" for f in acc["contract_files"])
    assert acc["default_decisions"] and acc["u_items"]               # 默认决策与 U-x 展示
    # 先确认前不可再次验收终态
    assert client.get(f"/api/projects/{pid}").json()["stage_status"]["9"] == "awaiting_acceptance"

    r = client.post(f"/api/projects/{pid}/acceptance", json={"reason": "核阅后确认交付"})
    assert r.status_code == 200, r.text
    detail = _wait(client, pid, {9: "done"})
    assert detail["stage_status"]["9"] == "done"
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert any(d["source"] == "final_acceptance" for d in ledger["decisions"])
    assert len(ledger["snapshots"]) == 10                            # 9 阶段 + 最终验收快照
    # 终态后不可重复验收
    assert client.post(f"/api/projects/{pid}/acceptance", json={}).status_code == 409


# ---- 4. deliberate 不变：两套结构变体 + 三方向 ----

def test_deliberate_keeps_two_variants_and_three_tiles(env):
    client, tmp = env
    pid = _mk_project(client, run_mode="auto", design_mode="deliberate")
    _stage1_manual(client, pid)
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    _wait(client, pid, {4: "awaiting_decision"})                    # 品味类停人工

    wdir = _ws_dir(tmp, pid)
    for s in ("S1", "S2"):
        assert (wdir / "04-wireframes" / f"{s}-v1.html").exists()
        assert (wdir / "04-wireframes" / f"{s}-v2.html").exists()   # 两套结构候选
    gal4 = client.get(f"/api/projects/{pid}/decision/4").json()["data"]
    assert all(len(it["options"]) == 2 for it in gal4["items"])
    client.post(f"/api/projects/{pid}/stages/4/decision", json={
        "answers": [{"id": it["id"], "answer": it["options"][0]["label"]} for it in gal4["items"]]})

    client.post(f"/api/projects/{pid}/stages/5/tasks")
    _wait(client, pid, {5: "awaiting_decision"})
    assert len(list((wdir / "05-style-tiles").glob("tile-*.html"))) == 3   # 三方向
    gal5 = client.get(f"/api/projects/{pid}/decision/5").json()["data"]
    assert len(gal5["items"][0]["options"]) == 3
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert not [d for d in ledger["decisions"] if d["source"] == "rapid_default"]


# ---- 6. rapid 下 L2 用模式化判据（引擎注入）；红色仍阻断 ----

def test_rapid_l2_mode_injected_and_red_still_blocks(env):
    client, _ = env
    pid = _mk_project(client, run_mode="auto", design_mode="rapid")
    _stage1_manual(client, pid)
    client.app.state.engine.reviewer = ScriptedReviewer([RED])       # 恒 🔴
    client.post(f"/api/projects/{pid}/stages/2/tasks")
    _wait(client, pid, {2: "done"})                                  # 兜底：failed 也会返回
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["stage_status"]["2"] == "failed_needs_human"       # rapid 不豁免红色
    row = client.app.state.db.query(
        "SELECT attempts, error FROM tasks WHERE project_id=? AND stage=2 ORDER BY id DESC LIMIT 1", (pid,))[0]
    assert row["attempts"] == 3 and "评审打回" in (row["error"] or "")
    # 模式由引擎注入评审器（评审器不自选）
    reviewer = client.app.state.engine.reviewer
    assert getattr(reviewer, "seen_modes", []) and "rapid" in reviewer.seen_modes


def test_claude_reviewer_prompt_carries_mode_context(tmp_path: Path):
    """评审 prompt 的模式块由引擎传入的 design_mode 决定：rapid 有模式上下文，deliberate 无。"""
    from backend.stages.registry import REGISTRY

    s = Settings(data_dir=tmp_path, runner="claude", reviewer="claude", task_timeout_s=1)
    reviewer = ClaudeReviewer(s)
    card = REGISTRY[4]
    rapid_prompt = reviewer.build_prompt(card, ["04-wireframes/S1-v1.html"], "rapid")
    deliberate_prompt = reviewer.build_prompt(card, ["04-wireframes/S1-v1.html"], "deliberate")
    # 以引擎注入块的标题为判据（公约/判据卡文本本身会提到模式感知，不能作区分）
    assert "## 模式上下文（引擎注入" in rapid_prompt and "not_applicable" in rapid_prompt
    assert "## 模式上下文（引擎注入" not in deliberate_prompt       # deliberate 无注入块，判据完全不变


def test_generation_prompt_carries_mode_block(tmp_path: Path):
    from backend.stages.registry import REGISTRY

    card = REGISTRY[4]
    ctx = {"product_name": "P", "project_name": "x", "platform": "mobile_app",
           "canvas_w": 390, "canvas_h": 844, "design_mode": "rapid"}
    rapid = card.build_prompt(ctx)
    assert "模式（引擎注入 · rapid 快速实现）" in rapid and "一套结构方案" in rapid
    ctx["design_mode"] = "deliberate"
    assert "模式（引擎注入" not in card.build_prompt(ctx)            # deliberate 无注入块


# ---- 7. rapid 阶段 8：有豁免必停人工；无豁免可继续（无豁免路径已由全链路测试覆盖） ----

def test_stage8_exemption_detection(tmp_path: Path):
    d = tmp_path / "proj"
    d.mkdir()
    (d / ".stage8-findings.json").write_text(json.dumps({
        "findings": [{"id": "F1", "severity": "yellow", "proposed": "exempt"}],
    }), encoding="utf-8")
    assert TaskEngine._stage8_has_exemptions(d) is True               # 有豁免 → 停人工
    (d / ".stage8-findings.json").write_text(json.dumps({
        "findings": [{"id": "F1", "severity": "yellow", "proposed": "spec"}],
    }), encoding="utf-8")
    assert TaskEngine._stage8_has_exemptions(d) is False              # 无豁免 → 可继续快速流程
    (d / ".stage8-findings.json").unlink()
    assert TaskEngine._stage8_has_exemptions(d) is True               # 读不到决策数据 → 不许自动放行
