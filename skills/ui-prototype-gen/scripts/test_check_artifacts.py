#!/usr/bin/env python3
"""check_artifacts.py 最小回归测试（零第三方依赖；pytest 兼容）。

覆盖：默认手机画布 390×844、Web 画布 1440×900（显式传参）、宽/高不匹配各自报错、
禁止词「这是」（及「欢迎」）、无 .frame 的 index 跳过画布检查、CLI 退出码与
--canvas-width/--canvas-height 传参、负面清单 html-conventions.md ↔ BANNED_COPY
逐词配平（防公约与脚本再漂移）。

用法：python skills/ui-prototype-gen/scripts/test_check_artifacts.py
     （pytest skills/ui-prototype-gen/scripts/test_check_artifacts.py 亦可）
退出码：0=全过，1=有失败。
"""

from __future__ import annotations

import contextlib
import io
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
