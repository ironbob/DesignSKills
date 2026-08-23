"""跨平台画布集成回归：三端预设生成→gate→预览数据链，不允许默认回退 390×844。

覆盖：mobile 390×844 / desktop 1280×800 / web 1440×900 的阶段 4、7 L1 gate 全过；
宽或高任一不一致必失败；canvas 缺失=配置错误必失败；MockRunner 罐头按项目画布
改写（.frame 宽高 / tokens.canvas / 文案字样）；桌面端 mock 九阶段走通出 spec。
"""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.engine.runner import MockRunner
from backend.platforms import PLATFORMS
from backend.stages.registry import GATES, REGISTRY

# ---------- 最小合格产物模板（按平台画布实例化） ----------

_FRAME_HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>S1</title><style>
.frame{width:{w}px;height:{h}px;box-sizing:border-box;display:flex;flex-direction:column;overflow:hidden;position:relative;background:#ffffff;border:1px solid #cccccc}
.fl{font-size:12px;color:#888888;text-align:center;margin-bottom:6px}
.a{flex:1;min-height:0;overflow:hidden;padding:16px}
.t{font-size:18px;color:#333333}
</style></head><body style="margin:0">
<div><div class="fl">① 常态</div><div class="frame"><div class="a"><div class="t">今日曲目：月光练习曲</div></div></div></div>
<div><div class="fl">② 空态（异常）</div><div class="frame"><div class="a"><div class="t">今日还没有曲目</div></div></div></div>
</body></html>
"""

_INDEX4 = """<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>对照板</title></head><body>
<h1>变体对照</h1><p>要决策的问题：反馈放哪——贴 A 还是固定 B？</p>
</body></html>
"""

_03_IA = """# 03 · 屏幕与IA

```mermaid
flowchart TD
    T1["今日"] --> S1["S1 今日任务卡"]
    S1 -->|"开始"| S2["S2 练习屏"]
```

| ID | 屏幕 | 层级 | 信息内容 | 操作 | 服务流程 | 模式倾向 |
|---|---|---|---|---|---|---|
| S1 | 今日任务卡 | Tab | 今日曲目 | **开始** | F1 | 卡片 |

## 闭环检查表

| 流程 | 覆盖屏幕 | 结论 |
|---|---|---|
| F1 | S1 → S2 | ✅ |

## 关键屏提名

- S1：第一印象屏。

## 新问题 P3-x

- P3-1 无。
"""


def _frame_html(w: int, h: int) -> str:
    return _FRAME_HTML.replace("{w}", str(w)).replace("{h}", str(h))


def _mk_stage47_workspace(tmp: Path, w: int, h: int) -> Path:
    d = tmp / "proj"
    (d / "04-wireframes").mkdir(parents=True)
    (d / "07-hifi").mkdir(parents=True)
    (d / "03-屏幕与IA.md").write_text(_03_IA, encoding="utf-8")
    for name in ("S1-v1.html", "S1-v2.html"):
        (d / "04-wireframes" / name).write_text(_frame_html(w, h), encoding="utf-8")
    (d / "04-wireframes" / "index.html").write_text(_INDEX4, encoding="utf-8")
    (d / "07-hifi" / "S1.html").write_text(_frame_html(w, h), encoding="utf-8")
    (d / "07-hifi" / "index.html").write_text(_INDEX4, encoding="utf-8")
    return d


@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_stage4_and_7_gate_pass_on_all_platform_presets(tmp_path: Path, platform: str):
    preset = PLATFORMS[platform]
    canvas = (preset["width"], preset["height"])
    d = _mk_stage47_workspace(tmp_path, *canvas)
    for stage in (4, 7):
        g = GATES[stage](None, d, canvas)
        assert g.ok, f"{platform} {canvas} 阶段 {stage} 应通过：{g.problems}"


@pytest.mark.parametrize("platform", sorted(PLATFORMS))
def test_width_or_height_mismatch_fails_gate(tmp_path: Path, platform: str):
    preset = PLATFORMS[platform]
    w, h = preset["width"], preset["height"]
    # 宽不一致
    d = _mk_stage47_workspace(tmp_path / "wide", w + 40, h)
    probs = GATES[4](None, d, (w, h)).problems
    assert any("[CANVAS]" in p and f"width:{w}px" in p for p in probs), probs
    # 高不一致
    d = _mk_stage47_workspace(tmp_path / "tall", w, h + 40)
    probs = GATES[7](None, d, (w, h)).problems
    assert any("[CANVAS]" in p and f"height:{h}px" in p for p in probs), probs


def test_stage4_gate_rejects_missing_canvas(tmp_path: Path):
    d = _mk_stage47_workspace(tmp_path, 390, 844)
    for stage in (4, 7):
        probs = GATES[stage](None, d, None).problems
        assert any("未提供项目画布" in p for p in probs), probs  # 不允许静默回退默认 390×844


def test_mock_runner_adapts_canned_artifacts_to_project_canvas(tmp_path: Path):
    """罐头按手机预制；Web 项目的 mock 复制须改写 .frame / tokens.canvas / 文案字样，且过 gate。"""
    canvas = (1440, 900)
    d = tmp_path / "proj"
    d.mkdir()

    async def _run(stage: int) -> None:
        card = REGISTRY[stage]

        async def step(text: str) -> None: ...
        async def art(path: str) -> None: ...

        await MockRunner(delay_s=0).run("prompt", d, card, step, art, canvas=canvas)

    asyncio.run(_run(3))
    asyncio.run(_run(4))
    assert GATES[4](None, d, canvas).ok
    wire = (d / "04-wireframes" / "S2-v1.html").read_text(encoding="utf-8")
    assert "width:1440px" in wire and "height:900px" in wire
    assert not re.search(r"(?<![a-zA-Z-])width:390px", wire)  # .frame 已改写（max-width 不受影响）

    asyncio.run(_run(6))
    import json as _json

    tokens = _json.loads((d / "06-tokens.json").read_text(encoding="utf-8"))
    assert (tokens["canvas"]["width"], tokens["canvas"]["height"]) == canvas
    assert GATES[6](None, d, canvas).ok

    asyncio.run(_run(7))
    assert GATES[7](None, d, canvas).ok


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("WB_DATA_DIR", str(tmp_path))
    from backend.main import create_app

    with TestClient(create_app()) as client:
        client.app.state.engine.runner = MockRunner(delay_s=0.02)
        yield client, tmp_path


def test_desktop_project_full_mock_flow_to_spec(env):
    """桌面 1280×800 预设：mock 九阶段走通，罐头画布已改写，最终 spec 落盘。"""
    client, tmp = env
    r = client.post(
        "/api/products",
        json={"name": "P", "requirement_doc": "# 需求\n桌面工具，多栏布局。",
              "project": {"name": "桌面App", "platform": "desktop_app", "run_mode": "auto"}},
    )
    pid = r.json()["projects"][0]["id"]

    client.post(f"/api/projects/{pid}/stages/1/tasks")
    deadline = time.monotonic() + 60

    def _wait(target_map: dict[int, str]) -> dict:
        while time.monotonic() < deadline:
            detail = client.get(f"/api/projects/{pid}").json()
            if all(detail["stage_status"].get(str(s)) == st for s, st in target_map.items()):
                return detail
            time.sleep(0.1)
        raise AssertionError(f"未到达 {target_map}（当前 {client.get(f'/api/projects/{pid}').json()['stage_status']}）")

    # 阶段 1 人工 → 2/3 代批 → 4 停人工（挑变体）→ 5 停 → 6/7 代批 → 8 停 → 9 代批
    _wait({1: "awaiting_decision"})
    data = client.get(f"/api/projects/{pid}/decision/1").json()["data"]
    client.post(f"/api/projects/{pid}/stages/1/decision", json={
        "answers": [{"id": q["id"], "answer": q["options"][0]["label"]} for q in data["blocking"]],
        "accepted_defaults": data.get("defaults", []),
    })
    client.post(f"/api/projects/{pid}/stages/2/tasks")  # 人工拍板不链式入队，手动发起；2/3 代批链到 4
    _wait({4: "awaiting_decision"})
    detail = client.get(f"/api/projects/{pid}").json()
    assert detail["canvas"] == {"width": 1280, "height": 800}
    for stage in (4, 5):
        _wait({stage: "awaiting_decision"})
        gal = client.get(f"/api/projects/{pid}/decision/{stage}").json()["data"]
        client.post(f"/api/projects/{pid}/stages/{stage}/decision", json={
            "answers": [{"id": it["id"], "answer": it["options"][0]["label"]} for it in gal["items"]],
        })
        client.post(f"/api/projects/{pid}/stages/{stage + 1}/tasks")
    _wait({8: "awaiting_decision"})
    crit = client.get(f"/api/projects/{pid}/decision/8").json()["data"]
    client.post(f"/api/projects/{pid}/stages/8/decision", json={
        "answers": [{"id": f["id"], "answer": f.get("proposed") or "fix"} for f in crit["yellows"]]
                    + [{"id": u["id"], "answer": u["proposal"]} for u in crit["u_items"]],
    })
    client.post(f"/api/projects/{pid}/stages/9/tasks")
    detail = _wait({9: "done"})

    wdir = tmp / "products" / "1" / "projects" / str(pid)
    hifi = (wdir / "07-hifi" / "S2.html").read_text(encoding="utf-8")
    assert "width:1280px" in hifi and "height:800px" in hifi and not re.search(r"(?<![a-zA-Z-])width:390px", hifi)
    tokens = (wdir / "06-tokens.json").read_text(encoding="utf-8")
    assert '"width": 1280' in tokens and '"height": 800' in tokens
    assert (wdir / "09-spec.md").exists()
    assert all(detail["stage_status"][str(s)] == "done" for s in range(1, 10))
