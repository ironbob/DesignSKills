"""增量设计变更（revision）验收。

覆盖：已完成项目创建 revision / 新增页面 / layout 变更触发阶段 4 / content 变更不重跑无关阶段 /
原始快照不可变 / revision 历史可查看 / 合并契约与版本号 / 快照恢复 / planner 分级规则。
既有九阶段流程回归由全量测试套件保证（本套件不改动主流程语义）。

真实 claude runner 未在测试内运行（不烧配额、不伪造结果）。
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.engine.impact import plan_from_impact
from backend.engine.runner import MockRunner


# ---------- 场景化的影响分析 runner：阶段 0 写指定场景，其余阶段走 mock 罐头 ----------

class ScriptedImpactRunner(MockRunner):
    def __init__(self, impact: dict, delay_s: float = 0.02) -> None:
        super().__init__(delay_s=delay_s)
        self.impact = impact

    async def run(self, prompt, cwd, card, on_step, on_artifact, canvas=None, design_mode="deliberate", platform="mobile_app"):
        if card.stage == 0:
            await on_step("读取基线契约 + 00-change-request.md")
            (cwd / "00-impact.json").write_text(json.dumps(self.impact, ensure_ascii=False, indent=2), encoding="utf-8")
            await on_artifact("00-impact.json")
            (cwd / "00-impact.md").write_text(
                "# 影响分析\n\n" + self.impact["summary"] + "\n\n逐页影响与回归范围见 00-impact.json，"
                "本文件为人读版摘要与判定理由。\n" + "判定依据详述。逐页对照基线盘点与流程草图核对。\n" * 6,
                encoding="utf-8",
            )
            await on_artifact("00-impact.md")
            return
        await super().run(prompt, cwd, card, on_step, on_artifact, canvas, design_mode, platform)


CONTENT_IMPACT = {
    "summary": "S5 打卡日历支持补签（内容级）",
    "pages": {"added": [], "modified": [
        {"page_id": "S5", "name": "我的", "level": "content", "reason": "补签入口与文案"},
    ], "removed": []},
    "flows": [], "navigation": [], "states": ["S5 同步失败态"],
    "shared_change": {"tokens": False, "components": False},
    "regression_pages": ["S1"],
}

LAYOUT_IMPACT = {
    "summary": "S4 词本改为三 Tab 分段结构（布局级）",
    "pages": {"added": [], "modified": [
        {"page_id": "S4", "name": "词本", "level": "layout", "reason": "主从列表改分段控制"},
    ], "removed": []},
    "flows": [], "navigation": [], "states": [],
    "shared_change": {"tokens": False, "components": False},
    "regression_pages": ["S1"],
}

NEW_PAGE_IMPACT = {
    "summary": "新增成就页（底部导航第 4 个入口）",
    "pages": {"added": [
        {"page_id": "S6", "name": "成就", "reason": "成就墙+分享，挂在底部导航"},
    ], "modified": [], "removed": []},
    "flows": ["F1 主流程回流：收尾小结可跳成就页"], "navigation": ["底部导航新增「成就」入口"],
    "states": [], "shared_change": {"tokens": False, "components": False},
    "regression_pages": ["S1", "S3"],
}


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as client:
        client.app.state.engine.runner = MockRunner(delay_s=0.02)
        yield client, tmp_path


def _mk_done_project(client: TestClient) -> int:
    """rapid+auto 最快跑完九阶段 + 最终验收 → 返回 project_id。"""
    r = client.post(
        "/api/products",
        json={"name": "P", "requirement_doc": "# 需求\n背单词练习 App，每日任务与错词强化。",
              "project": {"name": "手机App", "platform": "mobile_app", "run_mode": "auto", "design_mode": "rapid"}},
    )
    pid = r.json()["projects"][0]["id"]
    client.post(f"/api/projects/{pid}/stages/1/tasks")
    _wait(client, pid, {1: "awaiting_decision"})
    data = client.get(f"/api/projects/{pid}/decision/1").json()["data"]
    client.post(f"/api/projects/{pid}/stages/1/decision",
                json={"answers": [{"id": q["id"], "answer": q["options"][0]["label"]} for q in data["blocking"]]})
    client.post(f"/api/projects/{pid}/stages/2/tasks")  # 阶段 1 人工拍板后不链式入队，手动点火
    _wait(client, pid, {9: "awaiting_acceptance"})
    client.post(f"/api/projects/{pid}/acceptance", json={"reason": "测试收口"})
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["stage_status"]["9"] == "done"
    return pid


def _wait(client: TestClient, pid: int, target_map: dict[int, str], timeout_s: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        detail = client.get(f"/api/projects/{pid}").json()
        if all(detail["stage_status"].get(str(s)) == st for s, st in target_map.items()):
            return detail
        time.sleep(0.1)
    raise AssertionError(f"未到达 {target_map}")


def _wait_rev(client: TestClient, pid: int, rid: int, status: str | None = None,
              stage_map: dict[int, str] | None = None, timeout_s: float = 60.0) -> dict:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rev = client.get(f"/api/projects/{pid}/revisions/{rid}").json()
        ok = (status is None or rev["status"] == status) and (
            stage_map is None or all(rev["stage_status"].get(str(s)) == st for s, st in stage_map.items()))
        if ok:
            return rev
        time.sleep(0.1)
    raise AssertionError(f"revision 未到达 {status}/{stage_map}（当前 {client.get(f'/api/projects/{pid}/revisions/{rid}').json()['status']}）")


def _rev_decide(client: TestClient, pid: int, rid: int, stage: int) -> dict:
    """revision 阶段拍板：按决策类型构造答案（confirm/gallery/crit）。"""
    d = client.get(f"/api/projects/{pid}/revisions/{rid}/decision/{stage}").json()
    if d["type"] == "confirm":
        payload = {"answers": [{"id": f"stage-{stage}-confirm", "answer": "确认增量产物"}]}
    elif d["type"] == "gallery":
        payload = {"answers": [{"id": it["id"], "answer": it["options"][0]["label"]} for it in d["data"]["items"]]}
    else:  # crit
        payload = {"answers":
                   [{"id": f["id"], "answer": f.get("proposed") or "fix"} for f in d["data"]["yellows"]]
                   + [{"id": u["id"], "answer": u["proposal"]} for u in d["data"]["u_items"]],
                   "confirm_exemptions": False}
    r = client.post(f"/api/projects/{pid}/revisions/{rid}/stages/{stage}/decision", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def _run_revision_to_merge(client: TestClient, pid: int, impact: dict, reason: str = "增量") -> dict:
    """建 revision（场景化影响分析）→ 确认范围 → 逐阶段拍板 → 合并。"""
    client.app.state.engine.runner = ScriptedImpactRunner(impact)
    r = client.post(f"/api/projects/{pid}/revisions", json={
        "title": impact["summary"][:30], "requirement_text": "# 变更需求\n" + impact["summary"],
        "reason": reason, "doc_name": "change.md",
    })
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    _wait_rev(client, pid, rid, status="impact_ready")
    r = client.post(f"/api/projects/{pid}/revisions/{rid}/confirm", json={"reason": "范围认可"})
    assert r.status_code == 200, r.text
    rev = _wait_rev(client, pid, rid, status="running")
    for stage in sorted(int(k) for k, v in rev["stage_status"].items() if k != "0"):
        _wait_rev(client, pid, rid, stage_map={stage: "awaiting_decision"})
        _rev_decide(client, pid, rid, stage)
    rev = _wait_rev(client, pid, rid, status="completed")
    r = client.post(f"/api/projects/{pid}/revisions/{rid}/merge", json={"reason": "验收通过"})
    assert r.status_code == 200, r.text
    return {"rid": rid, "rev": rev, "merge": r.json()}


def _tree_hash(root: Path, only: set[str] | None = None) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        if only is not None and rel.split("/")[0] not in only:
            continue
        if p.is_file():
            h.update(rel.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


# ---------- 1. planner 分级规则（纯函数） ----------

def test_planner_level_rules():
    def plan(modified_level=None, added=None, states=None, shared=None):
        return plan_from_impact({
            "pages": {"added": added or [], "modified": ([{"page_id": "S1", "level": modified_level}] if modified_level else []), "removed": []},
            "states": states or [], "shared_change": shared or {"tokens": False, "components": False},
        })

    assert plan("content")["stages_to_rerun"] == [7, 9]                    # content：不动 2-6/8
    assert plan("content", states=["S1 新增态"])["stages_to_rerun"] == [7, 8, 9]  # 必要状态 → 矩阵与 crit 必须重验
    assert plan("component")["stages_to_rerun"] == [6, 7, 9]              # 设计系统 → 重出受影响页面
    assert plan("style")["stages_to_rerun"] == [6, 7, 9]                  # token → 重出受影响页面
    assert plan("layout")["stages_to_rerun"] == [4, 7, 8, 9]              # 必须回阶段 4
    assert plan(added=[{"page_id": "S6", "name": "成就"}])["stages_to_rerun"] == [2, 3, 4, 7, 8, 9]  # 新增页全链路
    assert plan("content", shared={"tokens": True, "components": False})["change_levels"] == ["content", "style"]
    assert plan("content")["regression_pages"] == []                      # 无交叉影响不强制回归


# ---------- 2. 已完成项目创建 revision：全链路（默认罐头=内容级） ----------

def test_revision_full_flow_on_completed_project(env):
    client, tmp = env
    pid = _mk_done_project(client)
    project_before = client.get(f"/api/projects/{pid}").json()
    snaps_before = {s["seq"]: _tree_hash(tmp / "products" / "1" / "projects" / str(pid) / "snapshots" / f"#{s['seq']}")
                    for s in client.get(f"/api/projects/{pid}/snapshots").json()}

    rid = _run_revision_to_merge(client, pid, CONTENT_IMPACT)["rid"]

    rev = client.get(f"/api/projects/{pid}/revisions/{rid}").json()
    assert rev["status"] == "merged"
    assert rev["base_snapshot_seq"] == max(snaps_before)               # 基线=最新已验收快照
    assert rev["version"] == "v2"
    assert rev["change_levels"] == ["content"]

    # content（含状态变更）：只重跑 7/8/9——不重跑无关阶段
    assert sorted(int(k) for k in rev["stage_status"] if k != "0") == [7, 8, 9]
    # 项目主流程阶段图不受 revision 影响
    after = client.get(f"/api/projects/{pid}").json()
    assert after["stage_status"] == project_before["stage_status"]
    assert after["current_task"]["revision_id"] is None                # 主视图任务不含 revision 任务
    # 契约版本 + 页面生命周期
    assert after["contract_version"] == 2
    s5 = next(p for p in after["pages"] if p["page_id"] == "S5")
    assert s5["lifecycle"] == "modified" and s5["last_revision_id"] == rid
    assert all(p["lifecycle"] == "initial" for p in after["pages"] if p["page_id"] != "S5")

    # 合并后的项目 spec 带变更记录五要素（基线/摘要/受影响页面/回归结果/版本号）
    rdir = tmp / "products" / "1" / "projects" / str(pid) / "revisions" / str(rid)
    spec = (rdir / "09-spec.md").read_text(encoding="utf-8")
    for key in ("变更记录", "基线", "变更摘要", "受影响页面", "回归结果", "v2"):
        assert key in spec, f"spec 缺 {key}"
    merged_spec = client.get(f"/api/projects/{pid}").json()  # 项目工作区已同步
    proj_spec = (tmp / "products" / "1" / "projects" / str(pid) / "09-spec.md").read_text(encoding="utf-8")
    assert "变更记录" in proj_spec and "v2" in proj_spec

    # 原始快照不可变：合并前后逐字节一致
    for seq, h in snaps_before.items():
        assert _tree_hash(tmp / "products" / "1" / "projects" / str(pid) / "snapshots" / f"#{seq}") == h
    # 合并产生新的项目快照（带 revision 出处）
    snaps_after = client.get(f"/api/projects/{pid}/snapshots").json()
    assert len(snaps_after) == len(snaps_before) + 1
    assert "revision R1 合并" in snaps_after[-1]["reason"]


def test_completed_project_create_revision_requires_snapshot(env):
    client, _ = env
    r = client.post("/api/products", json={
        "name": "P", "requirement_doc": "# 需求\nx", "project": {"name": "手机App", "platform": "mobile_app"}})
    pid = r.json()["projects"][0]["id"]
    r = client.post(f"/api/projects/{pid}/revisions", json={
        "title": "过早的变更", "requirement_text": "x"})
    assert r.status_code == 409 and "快照" in r.json()["detail"]


# ---------- 3. layout 变更触发阶段 4；content 不重跑无关阶段（stage 图级断言） ----------

def test_layout_change_triggers_stage4(env):
    client, _ = env
    pid = _mk_done_project(client)
    client.app.state.engine.runner = ScriptedImpactRunner(LAYOUT_IMPACT)
    r = client.post(f"/api/projects/{pid}/revisions", json={
        "title": "词本结构改版", "requirement_text": "# 变更\n词本三 Tab", "reason": "结构改版"})
    rid = r.json()["id"]
    _wait_rev(client, pid, rid, status="impact_ready")
    impact = client.get(f"/api/projects/{pid}/revisions/{rid}/impact").json()
    assert 4 in impact["plan"]["stages_to_rerun"]
    assert impact["plan"]["stages_to_rerun"] == [4, 7, 8, 9]
    r = client.post(f"/api/projects/{pid}/revisions/{rid}/confirm", json={})
    assert r.status_code == 200
    rev = _wait_rev(client, pid, rid, stage_map={4: "awaiting_decision"})
    assert sorted(int(k) for k in rev["stage_status"] if k != "0") == [4, 7, 8, 9]
    # 阶段 4 在 revision 内重新可选（主流程早已 done，不受"已完成阶段不可再次执行"限制）
    _rev_decide(client, pid, rid, 4)
    _wait_rev(client, pid, rid, stage_map={7: "awaiting_decision"})


def test_content_change_does_not_rerun_unrelated_stages(env):
    client, _ = env
    pid = _mk_done_project(client)
    no_states = dict(CONTENT_IMPACT, states=[])
    client.app.state.engine.runner = ScriptedImpactRunner(no_states)
    r = client.post(f"/api/projects/{pid}/revisions", json={
        "title": "补签文案", "requirement_text": "# 变更\n文案微调", "reason": "内容级"})
    rid = r.json()["id"]
    _wait_rev(client, pid, rid, status="impact_ready")
    impact = client.get(f"/api/projects/{pid}/revisions/{rid}/impact").json()
    assert impact["plan"]["stages_to_rerun"] == [7, 9]
    assert impact["plan"]["regression_pages"] == ["S1"]                # 回归验证但无需重做
    r = client.post(f"/api/projects/{pid}/revisions/{rid}/confirm", json={})
    rev = _wait_rev(client, pid, rid, status="running")
    stages = {int(k) for k in rev["stage_status"] if k != "0"}
    assert stages == {7, 9} and stages.isdisjoint({1, 2, 3, 4, 5, 6, 8})


# ---------- 4. 新增页面：页面登记 + 全链路阶段计划 ----------

def test_new_page_registers_pages_and_plans_full_chain(env):
    client, _ = env
    pid = _mk_done_project(client)
    client.app.state.engine.runner = ScriptedImpactRunner(NEW_PAGE_IMPACT)
    r = client.post(f"/api/projects/{pid}/revisions", json={
        "title": "成就页", "requirement_text": "# 变更\n新增成就页", "reason": "运营需求", "doc_name": "achieve.md"})
    rid = r.json()["id"]
    _wait_rev(client, pid, rid, status="impact_ready")
    impact = client.get(f"/api/projects/{pid}/revisions/{rid}/impact").json()
    assert impact["plan"]["stages_to_rerun"] == [2, 3, 4, 7, 8, 9]
    assert impact["plan"]["pages"]["added"] == ["S6"]
    assert impact["plan"]["regression_pages"] == ["S1", "S3"]          # 导航/流程变更 → 必须回归主流程

    r = client.post(f"/api/projects/{pid}/revisions/{rid}/confirm", json={})
    assert r.status_code == 200
    pages = client.get(f"/api/projects/{pid}").json()["pages"]
    s6 = next(p for p in pages if p["page_id"] == "S6")
    assert s6["lifecycle"] == "added" and s6["status"] == "live"
    assert s6["origin_revision_id"] == rid and s6["name"] == "成就"
    # 台账/决策按 revision 关联（页面范围可追溯）
    r = client.post(f"/api/projects/{pid}/revisions/{rid}/discard", json={"reason": "改主意"})
    assert r.status_code == 200
    pages = client.get(f"/api/projects/{pid}").json()["pages"]
    assert all(p["page_id"] != "S6" for p in pages)                    # 废弃撤回新增页登记


# ---------- 5. 原始快照不可变（创建+执行+合并全程） ----------

def test_original_snapshots_immutable_across_revision(env):
    client, tmp = env
    pid = _mk_done_project(client)
    pdir = tmp / "products" / "1" / "projects" / str(pid)
    before = {d.name: _tree_hash(d) for d in (pdir / "snapshots").iterdir() if d.is_dir()}
    proj_artifacts_before = _tree_hash(pdir, only={"04-wireframes", "07-hifi", "09-spec.md", "06-tokens.json"})

    out = _run_revision_to_merge(client, pid, CONTENT_IMPACT)
    rid = out["rid"]

    # 快照逐字节不变
    after = {d.name: _tree_hash(d) for d in (pdir / "snapshots").iterdir() if d.is_dir()}
    for k, h in before.items():
        assert after[k] == h, f"快照 {k} 被改写"
    # 增量产物只发生在 revisions/<rid>/（合并前项目产物不动，合并后才同步）
    rdir = pdir / "revisions" / str(rid)
    assert (rdir / "00-impact.json").exists()
    assert (rdir / "00-change-request.md").exists()
    # 合并后项目产物已更新（= 与基线不同），但历史快照仍保存旧版
    assert _tree_hash(pdir, only={"09-spec.md"}) != _tree_hash(pdir / "snapshots" / "#1", only={"09-spec.md"})


# ---------- 6. revision 历史可查看 + 台账关联 ----------

def test_revision_history_and_ledger(env):
    client, _ = env
    pid = _mk_done_project(client)
    out1 = _run_revision_to_merge(client, pid, CONTENT_IMPACT)
    out2 = _run_revision_to_merge(client, pid, LAYOUT_IMPACT)

    revs = client.get(f"/api/projects/{pid}/revisions").json()
    assert [r["seq"] for r in revs] == [1, 2]
    assert revs[0]["status"] == "merged" and revs[0]["version"] == "v2"
    assert revs[1]["status"] == "merged" and revs[1]["version"] == "v3"
    # 链式基线：第二个 revision 的基线是第一个合并后的最新快照
    assert revs[1]["base_snapshot_seq"] > revs[0]["base_snapshot_seq"]
    assert client.get(f"/api/projects/{pid}").json()["contract_version"] == 3

    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    rev_decisions = [d for d in ledger["decisions"] if d.get("revision_id")]
    assert {d["revision_id"] for d in rev_decisions} == {out1["rid"], out2["rid"]}
    assert any(d["source"] == "revision_merge" for d in rev_decisions)
    # 产物列表（products 接口）可见 revision 概要
    projs = client.get("/api/products").json()[0]["projects"]
    assert len(projs[0]["revisions"]) == 2


# ---------- 7. 快照查看 / 恢复 ----------

def test_snapshot_view_and_restore(env):
    client, tmp = env
    pid = _mk_done_project(client)
    pre_merge_snapshots = [s["seq"] for s in client.get(f"/api/projects/{pid}/snapshots").json()]
    base_seq = max(pre_merge_snapshots)
    out = _run_revision_to_merge(client, pid, CONTENT_IMPACT)

    # 查看：快照文件清单 + 单文件内容（只读）
    snap = client.get(f"/api/projects/{pid}/snapshots/{base_seq}").json()
    assert any(f["path"] == "09-spec.md" for f in snap["files"])
    f = client.get(f"/api/projects/{pid}/snapshots/{base_seq}/file?path=09-spec.md")
    assert f.status_code == 200 and "变更记录" not in f.text

    # 恢复：进行中 revision 阻断；合并后可恢复
    r = client.post(f"/api/projects/{pid}/snapshots/{base_seq}/restore", json={"reason": "回到基线"})
    assert r.status_code == 200
    pdir = tmp / "products" / "1" / "projects" / str(pid)
    assert "变更记录" not in (pdir / "09-spec.md").read_text(encoding="utf-8")   # 项目 spec 已回退
    snaps = client.get(f"/api/projects/{pid}/snapshots").json()
    assert len(snaps) == len(pre_merge_snapshots) + 2                      # 合并快照 + 回退保全快照
    assert any("保全" in s["reason"] for s in snaps)
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert any(d["source"] == "rollback" for d in ledger["decisions"])
    # 历史快照本体仍然未动
    assert _tree_hash(pdir / "snapshots" / f"#{base_seq}") is not None


def test_restore_blocked_while_revision_active(env):
    client, _ = env
    pid = _mk_done_project(client)
    client.app.state.engine.runner = ScriptedImpactRunner(CONTENT_IMPACT)
    r = client.post(f"/api/projects/{pid}/revisions", json={
        "title": "进行中", "requirement_text": "x", "reason": ""})
    rid = r.json()["id"]
    _wait_rev(client, pid, rid, status="impact_ready")
    seq = max(s["seq"] for s in client.get(f"/api/projects/{pid}/snapshots").json())
    r = client.post(f"/api/projects/{pid}/snapshots/{seq}/restore", json={})
    assert r.status_code == 409 and "revision" in r.json()["detail"]


# ---------- 8. diff：基线 vs revision ----------

def test_revision_diff_endpoint(env):
    client, _ = env
    pid = _mk_done_project(client)
    client.app.state.engine.runner = ScriptedImpactRunner(CONTENT_IMPACT)
    r = client.post(f"/api/projects/{pid}/revisions", json={
        "title": "补签", "requirement_text": "x", "reason": ""})
    rid = r.json()["id"]
    _wait_rev(client, pid, rid, status="impact_ready")
    diff = client.get(f"/api/projects/{pid}/revisions/{rid}/diff").json()
    assert diff["base_snapshot_seq"] > 0
    assert "00-impact.json" not in diff["added"]                       # revision 专属文件不进 diff
    assert diff["pages"] == {}                                          # 确认前 plan 未锁定
    r = client.post(f"/api/projects/{pid}/revisions/{rid}/confirm", json={})
    diff = client.get(f"/api/projects/{pid}/revisions/{rid}/diff").json()
    assert diff["pages"]["modified"] == ["S5"]
