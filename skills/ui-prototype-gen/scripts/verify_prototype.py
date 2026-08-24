#!/usr/bin/env python3
"""Browser-level verification for 08-prototype.html (stage-8 completion flag).

check_artifacts.py proves structure statically: sidebar, device-frame lock,
manifest parses / no dangling targets / coverage / reachability / section sync.
It cannot prove that clicks actually move the phone. This script drives a real
headless browser through every manifest route and asserts the visible
screen/state follows — the manifest doubles as the click test script.

Needs:  pip install playwright && playwright install chromium
Without Playwright it prints the manual checklist (derived from the manifest)
and exits 3 (NOT RUN) — the stage-8 gate then demands the checklist executed
by a human, results recorded in 08-findings.md / handoff notes.

Usage:  verify_prototype.py <08-prototype.html> [--timeout 15000]
Exit:   0 all routes verified · 1 failures · 2 bad input · 3 playwright missing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

MANIFEST_RE = re.compile(
    r'<script\b[^>]*\bid="interaction-manifest"[^>]*>(.*?)</script>', re.DOTALL
)

# input 路由的驱动文本：to 为 error 态填非法简谱（触发校验失败），否则填合法简谱。
# 与样例原型 validator 约定一致：音高记号 1–7 合法、8 非法。按项目领域替换。
INVALID_INPUT = "1=D 4/4\n1 2 3 5 | 6 5 3 8 |"
VALID_INPUT = "1=D 4/4\n1 2 3 5 | 6 5 3 2 |"


def _current_node_js() -> str:
    return (
        "(() => { const el = document.querySelector('.app-screen.is-active');"
        " return el ? el.dataset.screen + '@' + el.dataset.state : null; })()"
    )


def _load_manifest(html: str) -> dict:
    m = MANIFEST_RE.search(html)
    if not m:
        raise SystemExit("未找到 interaction manifest（先过 check_artifacts.py）")
    return json.loads(m.group(1))


def _bfs_path(routes: list[dict], start: str, goal: str) -> list[dict] | None:
    """start→goal 的最短路由序列（真实点击路径）。"""
    if start == goal:
        return []
    prev: dict[str, tuple[str, dict]] = {}
    seen, queue = {start}, [start]
    while queue:
        cur = queue.pop(0)
        for r in routes:
            if r.get("from") == cur and r.get("to") not in seen:
                seen.add(r["to"])
                prev[r["to"]] = (cur, r)
                if r["to"] == goal:
                    path, node = [], r["to"]
                    while node != start:
                        node, edge = prev[node][0], prev[node][1]
                        path.append(edge)
                    return list(reversed(path))
                queue.append(r["to"])
    return None


def _drive_route(page, route: dict) -> None:
    ctl = route["control"]
    if route.get("event") == "input":
        bad = "error" in route.get("tags", [])
        page.fill(ctl, INVALID_INPUT if bad else VALID_INPUT)
        return
    page.click(ctl)


def run_browser(path: Path, timeout_ms: int) -> int:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    manifest = _load_manifest(path.read_text(encoding="utf-8"))
    routes = manifest["routes"]
    entry = manifest["meta"]["entry"]
    failures: list[str] = []
    checked = 0

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(timeout_ms)
        page.goto(path.resolve().as_uri())

        current = page.evaluate(_current_node_js())
        if current != entry:
            failures.append(f"初始节点 {current!r} ≠ meta.entry {entry!r}")

        # 侧栏浏览入口：每个 data-goto 可点且手机切屏
        for goto in page.eval_on_selector_all("[data-goto]", "els => els.map(e => e.dataset.goto)"):
            page.click(f'[data-goto="{goto}"]')
            now = page.evaluate(_current_node_js())
            if "@" in goto and now != goto:
                failures.append(f"侧栏 {goto} 点击后节点 {now!r} ≠ {goto!r}")
            elif now.split("@")[0] != goto.split("@")[0]:
                failures.append(f"侧栏 {goto} 点击后未切到该屏（当前 {now!r}）")

        # 每条路由：先真实点击走到 from，再触发控件，断言切到 to
        page.click(f'[data-goto="{entry.split("@")[0]}"]')
        current = page.evaluate(_current_node_js())
        for r in routes:
            rid = r.get("id", f"{r['from']}->{r['to']}")
            path_routes = _bfs_path(routes, current, r["from"])
            if path_routes is None:
                failures.append(f"路由 {rid}: 无法从 {current!r} 走到 from {r['from']!r}")
                continue
            try:
                for step in path_routes:
                    _drive_route(page, step)
                _drive_route(page, r)
                now = page.evaluate(_current_node_js())
                checked += 1
                if now != r["to"]:
                    failures.append(f"路由 {rid}: 触发后节点 {now!r} ≠ 声明 to {r['to']!r}")
                else:
                    print(f"OK   {rid}: {r['from']} --[{r.get('event')}/{r.get('label')}]--> {r['to']}")
                current = now
            except Exception as exc:  # noqa: BLE001 — 控件缺失/不可点都要报告
                checked += 1
                failures.append(f"路由 {rid}: 驱动失败 {exc.__class__.__name__}: {exc}")
                page.click(f'[data-goto="{entry.split("@")[0]}"]')
                current = page.evaluate(_current_node_js())

        browser.close()

    print(f"— {checked}/{len(routes)} 条路由已驱动，{len(failures)} 处失败")
    for f in failures:
        print(f"FAIL {f}")
    return 1 if failures else 0


MANUAL_STEPS = [
    "1. 页面列表每个页面项点击后，手机切到对应页面/状态，列表高亮同步移动；",
    "2. 主流程仅用手机内控件从起点走到成功出口，逐段有可见状态反馈；",
    "3. 异常/校验失败态可见（错误定位、保存禁用），修复后可保存；",
    "4. 取消/返回路径可用，异常路径可返回；",
    "5. 「重置流程」后回到确定初始状态（meta.entry）；",
    "6. 断网双击打开可运行（无外部请求）。",
]


def print_manual_checklist(manifest: dict) -> None:
    print("未安装 Playwright（pip install playwright && playwright install chromium），"
          "改出手工验证清单——逐项执行并把结果记入 08-findings.md / 交付说明：")
    for step in MANUAL_STEPS:
        print(" ", step)
    print("  manifest 路由清单（逐条核对 控件→目标态→反馈）：")
    for r in manifest["routes"]:
        print(f"    [{r.get('id','?')}] {r['from']} --({r.get('event')}/{r.get('label')})--> "
              f"{r['to']}  预期反馈: {r.get('feedback','')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="browser-verify 08-prototype.html against its manifest")
    parser.add_argument("path", type=Path)
    parser.add_argument("--timeout", type=int, default=15000, help="单步超时毫秒")
    args = parser.parse_args()
    if not args.path.is_file():
        print(f"[IO] 文件不存在: {args.path}", file=sys.stderr)
        return 2
    html = args.path.read_text(encoding="utf-8")
    try:
        manifest = _load_manifest(html)
    except (json.JSONDecodeError, SystemExit) as exc:
        print(f"[MANIFEST] 解析失败: {exc}", file=sys.stderr)
        return 2

    try:
        from playwright.sync_api import sync_playwright  # noqa: F401, PLC0415
    except ImportError:
        print_manual_checklist(manifest)
        return 3
    return run_browser(args.path, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
