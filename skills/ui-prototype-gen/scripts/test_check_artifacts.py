#!/usr/bin/env python3
"""check_artifacts.py 最小回归测试（零第三方依赖；pytest 兼容）。

覆盖：默认手机画布 390×844、Web 画布 1440×900（显式传参）、宽/高不匹配各自报错、
禁止词「这是」（及「欢迎」）、无 .frame 的 index 跳过画布检查、CLI 退出码与
--canvas-width/--canvas-height/--platform 传参、负面清单 html-conventions.md ↔
BANNED_COPY 逐词配平（防公约与脚本再漂移）。

新增 PROTOTYPE 查覆盖：mobile 平台 08-prototype.html 必须为工作台（缺壳报错、
desktop 平台豁免）、工作台缺侧栏/说明面板/锁定 device-frame 报错、manifest 悬空
目标/五类覆盖缺失/出口不可达/死节点报错、HTML section ↔ manifest 双向同步、侧栏
data-goto 悬空与缺页报错、event 词表、外部资源引用（DEPS）报错、完整工作台绿。

用法：python skills/ui-prototype-gen/scripts/test_check_artifacts.py
     （pytest skills/ui-prototype-gen/scripts/test_check_artifacts.py 亦可）
退出码：0=全过，1=有失败。
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_artifacts  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parents[1]


def _frame_html(width: int, height: int, body: str = "<span>练习曲目一</span>") -> str:
    return (
        "<!doctype html><html><head><style>"
        f".frame{{width:{width}px;height:{height}px;display:flex;overflow:hidden;position:relative}}"
        "</style></head><body><div class='frame'><div>演奏厅</div>" + body + "</div></body></html>"
    )


def _manifest(routes: list[dict], screens: list[dict] | None = None, entry: str = "s1@default") -> str:
    manifest = {
        "meta": {"project": "回归样例", "entry": entry},
        "screens": screens
        or [
            {"id": "s1", "name": "库", "module": "主流程", "states": ["default"]},
            {"id": "s2", "name": "详情", "module": "主流程", "states": ["default"]},
            {"id": "s3", "name": "录入", "module": "录谱", "states": ["draft", "error", "ok"]},
        ],
        "routes": routes,
    }
    return json.dumps(manifest, ensure_ascii=False)


_BASE_ROUTES = [
    {"id": "r1", "from": "s1@default", "control": "[data-action=open]", "label": "曲目行",
     "event": "tap", "to": "s2@default", "feedback": "进入详情", "tags": ["main"]},
    {"id": "r2", "from": "s2@default", "control": "[data-action=edit]", "label": "去录入",
     "event": "tap", "to": "s3@draft", "feedback": "进入录入", "tags": ["main"]},
    {"id": "r3", "from": "s3@draft", "control": "#input", "label": "输入非法记号",
     "event": "input", "to": "s3@error", "feedback": "错误定位+保存禁用", "tags": ["error"]},
    {"id": "r4", "from": "s3@error", "control": "#input", "label": "修正",
     "event": "input", "to": "s3@draft", "feedback": "恢复可保存", "tags": ["recover"]},
    {"id": "r5", "from": "s2@default", "control": "[data-action=back]", "label": "返回",
     "event": "back", "to": "s1@default", "feedback": "回到库", "tags": ["cancel"]},
    {"id": "r6", "from": "s3@draft", "control": "[data-action=save]", "label": "保存",
     "event": "submit", "to": "s3@ok", "feedback": "保存成功", "tags": ["success"]},
]


def _workbench_html(
    *,
    manifest: str | None = None,
    sections: tuple[str, ...] = ("s1@default", "s2@default", "s3@draft", "s3@error", "s3@ok"),
    gotos: tuple[str, ...] = ("s1", "s2", "s3"),
    sidebar: bool = True,
    caption: bool = True,
    device_rule: str = ".device-frame{width:390px;height:844px;overflow:hidden}",
    external: str = "",
) -> str:
    nav = "".join(
        f'<button class="page-item" data-goto="{g}">{g}</button>' for g in gotos
    )
    secs = "".join(
        f'<section class="app-screen" data-screen="{n.split("@")[0]}" '
        f'data-state="{n.split("@")[1]}"><span>屏 {n}</span></section>'
        for n in sections
    )
    sidebar_html = f'<aside class="workbench-sidebar"><nav>{nav}</nav></aside>' if sidebar else ""
    caption_html = '<div class="device-caption"><span>当前状态</span></div>' if caption else ""
    m = manifest if manifest is not None else _manifest(list(_BASE_ROUTES))
    return (
        "<!doctype html><html><head><style>"
        ".prototype-workbench{display:flex}"
        ".workbench-sidebar{width:280px}"
        + device_rule
        + "</style></head><body>"
        '<div class="prototype-workbench">'
        + sidebar_html
        + '<main class="workbench-stage"><div class="device-frame">' + secs + "</div>"
        + caption_html
        + "</main></div>"
        + external
        + '<script type="application/json" id="interaction-manifest">' + m + "</script>"
        + "<script>/* go() 状态机 */</script>"
        + "</body></html>"
    )


def _write(tmp: str, name: str, html: str) -> Path:
    p = Path(tmp) / name
    p.write_text(html, encoding="utf-8")
    return p


def test_default_mobile_canvas_pass():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "s1.html", _frame_html(390, 844))
        assert check_artifacts.check_file(p, 390, 844) == []


def test_web_canvas_1440x900_with_flags():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "s1.html", _frame_html(1440, 900))
        assert check_artifacts.check_file(p, 1440, 900) == []
        # 不传参（默认 390×844）必须拦下 Web 画布文件——默认不是唯一合法尺寸，但缺省即手机
        assert any("[CANVAS]" in x for x in check_artifacts.check_file(p, 390, 844))


def test_width_mismatch_and_height_mismatch_reported_separately():
    with tempfile.TemporaryDirectory() as d:
        wide = _write(d, "w.html", _frame_html(390, 900))  # 宽不匹配（项目画布 1440×900）
        probs = check_artifacts.check_file(wide, 1440, 900)
        assert any("[CANVAS]" in x and "width:1440px" in x and "height" not in x for x in probs)
        tall = _write(d, "h.html", _frame_html(1440, 844))  # 高不匹配
        probs = check_artifacts.check_file(tall, 1440, 900)
        assert any("[CANVAS]" in x and "height:900px" in x and "width" not in x for x in probs)


def test_banned_word_zheshi_and_huanying():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "bad.html", _frame_html(390, 844, body="<span>这是最后一步</span>"))
        assert any("[COPY]" in x and "这是" in x for x in check_artifacts.check_file(p, 390, 844))
        p2 = _write(d, "bad2.html", _frame_html(390, 844, body="<span>欢迎使用向导</span>"))
        assert any("[COPY]" in x and "欢迎" in x for x in check_artifacts.check_file(p2, 390, 844))


def test_index_without_frame_skips_canvas_check():
    html = (
        "<!doctype html><html><head><style>.board{display:flex;gap:40px}</style></head>"
        "<body><div class='board'><span>变体对照板</span></div></body></html>"
    )
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "index.html", html)
        assert check_artifacts.check_file(p, 1440, 900) == []


def test_cli_flags_and_exit_codes():
    argv = sys.argv
    try:
        with tempfile.TemporaryDirectory() as d:
            ok = _write(d, "ok.html", _frame_html(1440, 900))
            _write(d, "bad.html", _frame_html(1440, 800))  # 高不匹配
            base = ["check_artifacts.py"]
            with contextlib.redirect_stdout(io.StringIO()):
                sys.argv = base + [str(ok), "--canvas-width", "1440", "--canvas-height", "900"]
                assert check_artifacts.main() == 0  # 传参匹配 → 绿
                sys.argv = base + [str(d), "--canvas-width", "1440", "--canvas-height", "900"]
                assert check_artifacts.main() == 1  # 目录含 bad.html → ERROR
                sys.argv = base + [str(ok)]
                assert check_artifacts.main() == 1  # 缺省 390×844 → Web 文件被拦
    finally:
        sys.argv = argv


def test_banned_list_in_sync_with_conventions():
    """公约 §4 负面清单 ↔ 脚本 BANNED_COPY 逐词配平（漂移即红）。"""
    text = (SKILL_DIR / "references" / "html-conventions.md").read_text(encoding="utf-8")
    section = text.split("## 4.")[1].split("## 5.")[0]
    # 只取以反引号开头的行（清单行本身）；同步说明句以汉字开头，不参与解析
    words = {
        w
        for line in section.splitlines()
        if line.strip().startswith("`")
        for w in re.findall(r"`([^`]+)`", line)
    }
    assert words and "这是" in words, "公约负面清单应能解析且含「这是」"
    script_words = set(check_artifacts.BANNED_COPY)
    assert words == script_words, (
        f"清单漂移：仅公约={sorted(words - script_words)}；仅脚本={sorted(script_words - words)}"
    )


# ---- PROTOTYPE 查（mobile 工作台契约） ----


def test_full_workbench_passes():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "08-prototype.html", _workbench_html())
        assert check_artifacts.check_file(p, 390, 844, "mobile") == []


def test_mobile_prototype_without_workbench_flagged_and_desktop_exempt():
    plain = _frame_html(1440, 900)  # 桌面形态可点原型（非工作台）
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "08-prototype.html", plain)
        probs = check_artifacts.check_file(p, 1440, 900, "mobile")
        assert any("[WORKBENCH]" in x and "工作台" in x for x in probs)
        assert check_artifacts.check_file(p, 1440, 900, "desktop") == []
        assert check_artifacts.check_file(p, 1440, 900, "web") == []


def test_workbench_missing_sidebar_or_caption_flagged():
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "08-prototype.html", _workbench_html(sidebar=False))
        assert any("[WORKBENCH]" in x and "workbench-sidebar" in x
                   for x in check_artifacts.check_file(p, 390, 844, "mobile"))
        p2 = _write(d, "08-prototype.html", _workbench_html(caption=False))
        assert any("[WORKBENCH]" in x and "device-caption" in x
                   for x in check_artifacts.check_file(p2, 390, 844, "mobile"))


def test_device_frame_must_lock_canvas():
    with tempfile.TemporaryDirectory() as d:
        p = _write(
            d, "08-prototype.html",
            _workbench_html(device_rule=".device-frame{width:100%;height:844px}"),
        )
        probs = check_artifacts.check_file(p, 390, 844, "mobile")
        assert any("[CANVAS]" in x and "device-frame" in x and "width:390px" in x for x in probs)
        assert not any(".frame" in x for x in probs)  # 工作台外壳不被套用 .frame 校验


def test_manifest_dangling_target_flagged():
    routes = list(_BASE_ROUTES) + [
        {"id": "r6", "from": "s1@default", "control": "[data-action=ghost]", "label": "幽灵",
         "event": "tap", "to": "ghost@default", "feedback": "悬空", "tags": ["main"]}
    ]
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "08-prototype.html", _workbench_html(manifest=_manifest(routes)))
        assert any("[MANIFEST]" in x and "悬空目标" in x and "ghost@default" in x
                   for x in check_artifacts.check_file(p, 390, 844, "mobile"))


def test_manifest_coverage_and_event_vocabulary():
    no_cancel = [r for r in _BASE_ROUTES if "cancel" not in r.get("tags", [])]
    bad_event = [dict(r, event="hover") if r["id"] == "r5" else r for r in _BASE_ROUTES]
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "08-prototype.html", _workbench_html(manifest=_manifest(no_cancel)))
        assert any("[MANIFEST]" in x and "五类覆盖缺失" in x and "cancel" in x
                   for x in check_artifacts.check_file(p, 390, 844, "mobile"))
        p2 = _write(d, "08-prototype.html", _workbench_html(manifest=_manifest(bad_event)))
        assert any("[MANIFEST]" in x and "event 非法" in x
                   for x in check_artifacts.check_file(p2, 390, 844, "mobile"))


def test_manifest_success_unreachable_and_dead_nodes():
    # 砍掉 r3/r4（draft⇄error 互达），success 路由 r6 挂在孤岛 s3@error 上：
    # s3@error、s3@ok 均不可达，且 entry 经手机内路由到不了 success 出口
    broken = [r for r in _BASE_ROUTES if r["id"] not in ("r3", "r4", "r6")]
    broken.append({"id": "r6", "from": "s3@error", "control": "[data-action=save]", "label": "保存",
                   "event": "submit", "to": "s3@ok", "feedback": "保存成功", "tags": ["success"]})
    with tempfile.TemporaryDirectory() as d:
        p = _write(d, "08-prototype.html", _workbench_html(manifest=_manifest(broken)))
        probs = check_artifacts.check_file(p, 390, 844, "mobile")
        assert any("success 出口不可达" in x for x in probs)
        assert any("不可达的屏状态" in x and "s3@error" in x for x in probs)


def test_sync_sections_and_sidebar_goto():
    with tempfile.TemporaryDirectory() as d:
        # section 缺 s3@ok + 多出未声明 s4@default
        p = _write(
            d, "08-prototype.html",
            _workbench_html(sections=("s1@default", "s2@default", "s3@draft", "s3@error",
                                      "s4@default")),
        )
        probs = check_artifacts.check_file(p, 390, 844, "mobile")
        assert any("缺 HTML section" in x and "s3@ok" in x for x in probs)
        assert any("未在 manifest 声明" in x and "s4@default" in x for x in probs)
        # 侧栏：data-goto 悬空 + 缺 s3 页面项
        p2 = _write(d, "08-prototype.html", _workbench_html(gotos=("s1", "s2", "nope")))
        probs2 = check_artifacts.check_file(p2, 390, 844, "mobile")
        assert any("data-goto 指向未声明目标" in x and "nope" in x for x in probs2)
        assert any("侧栏缺少页面项" in x and "s3" in x for x in probs2)


def test_external_resources_rejected():
    with tempfile.TemporaryDirectory() as d:
        p = _write(
            d, "08-prototype.html",
            _workbench_html(external='<img src="https://cdn.example.net/logo.png" alt="曲库">'),
        )
        assert any("[DEPS]" in x for x in check_artifacts.check_file(p, 390, 844, "mobile"))
        p2 = _write(
            d, "index.html",
            "<!doctype html><html><head><style>@import url('https://fonts.example.net/css');</style>"
            "</head><body><div><span>对照板</span></div></body></html>",
        )
        assert any("[DEPS]" in x for x in check_artifacts.check_file(p2, 1440, 900, "web"))


def test_cli_platform_flag():
    argv = sys.argv
    try:
        with tempfile.TemporaryDirectory() as d:
            wb = _write(d, "08-prototype.html", _workbench_html())
            plain = _write(d, "plain.html", _frame_html(1440, 900))
            base = ["check_artifacts.py"]
            with contextlib.redirect_stdout(io.StringIO()):
                sys.argv = base + [str(wb)]
                assert check_artifacts.main() == 0  # mobile 默认 + 工作台 → 绿
                sys.argv = base + [str(plain), "--platform", "desktop",
                                   "--canvas-width", "1440", "--canvas-height", "900"]
                assert check_artifacts.main() == 0  # desktop 平台豁免工作台要求
    finally:
        sys.argv = argv


def _run_all() -> int:
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as e:
            failed.append(name)
            print(f"FAIL {name}: {e}")
    print(f"— {len(tests) - len(failed)}/{len(tests)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
