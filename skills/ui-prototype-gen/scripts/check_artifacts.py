#!/usr/bin/env python3
"""Artifact integrity gate for ui-prototype-gen HTML outputs.

Checks, all earned the hard way on a real project:
  TAG       div/span open/close balance (a stray </div> breaks a whole frame)
  CANVAS    files that define a .frame rule must lock BOTH its width and height
            to the project canvas (default mobile 390x844; adaptive size hides
            density/overflow problems and misplaces overlays); prototype
            workbenches lock their inner .device-frame instead — the desktop
            shell itself stays responsive and is NOT canvas-checked
  COPY      banned-copy sweep over visible text (欢迎/示例/占位/lorem/... exist
            only when the model hedges by addition)
  PROTOTYPE stage-8 interactive-prototype contract (mobile workbench):
            WORKBENCH   --platform mobile (default) makes 08-prototype.html a
                        workbench: .prototype-workbench shell + sidebar +
                        canvas-locked .device-frame + .device-caption + inline
                        interaction manifest
            MANIFEST   the <script id="interaction-manifest"> JSON parses; every
                       route from/to node exists (no dangling targets); event
                       vocabulary enforced; coverage tags main/success/cancel/
                       error/recover each present; entry reaches a success exit
                       via in-phone routes; every screen@state reachable (routes
                       or sidebar browse)
            SYNC       phone sections (data-screen/data-state) match the
                       manifest node set both ways; sidebar items (data-goto)
                       reference manifest screens/states and cover every screen
  DEPS      self-containment for ALL files: no external http(s) resources
            (src/href/@import/url()) — the prototype must run offline, opened
            by double-click, with no framework dependency

Usage: check_artifacts.py <path>... [--canvas-width 390] [--canvas-height 844]
                          [--platform mobile|desktop|web]
       canvas args = the project's target canvas (web tool passes the locked
       platform preset); standalone skill defaults to mobile 390x844.
       platform = tokens target (default mobile): under mobile, 08-prototype*.html
       MUST be a workbench; desktop/web keeps the plain clickable prototype.
Exit:  0 all green, 1 any ERROR, 2 nothing to check.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 负面文案清单：与 references/html-conventions.md §4 一一对应，改任何一侧必须
# 同步另一处（scripts/test_check_artifacts.py 有配平断言防再漂移）。
BANNED_COPY = [
    "欢迎", "欢迎使用", "本页面", "本页用于", "该页面", "示例文本", "示例：",
    "占位", "待补充", "待填写", "lorem", "ipsum", "TODO", "FIXME",
    "点击这里", "此处显示", "xxx", "XXX", "???", "测试数据", "假数据",
    "这是", "以上是",
]

WORKBENCH_MARKER = "prototype-workbench"
MANIFEST_RE = re.compile(
    r'<script\b[^>]*\bid="interaction-manifest"[^>]*>(.*?)</script>', re.DOTALL
)
SECTION_TAG_RE = re.compile(r"<section\b[^>]*>")
GOTO_RE = re.compile(r'data-goto="([^"]+)"')
VALID_EVENTS = ("tap", "input", "select", "submit", "back", "reset")
COVERAGE_TAGS = ("main", "success", "cancel", "error", "recover")
EXTERNAL_RES_RE = re.compile(
    r'(?:\b(?:src|href)\s*=\s*["\']https?://)'
    r'|(@import\s+(?:url\()?\s*["\']?https?://)'
    r'|(\burl\(\s*["\']?https?://)',
    re.IGNORECASE,
)


def strip_to_text(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"<[^>]+>", " ", html)


def _locked(css_rule: str, prop: str, value: int) -> bool:
    """规则里存在 `prop:value px` 声明（min-/max- 前缀不冒充锁定值）。"""
    decl = re.sub(r"\s+", "", css_rule)
    return re.search(rf"(?<![a-zA-Z-]){prop}:{value}px(?![0-9])", decl) is not None


def _has_element(html: str, cls: str) -> bool:
    """存在带该 class 的元素（只出现在 CSS 规则里不算——元素级检测）。"""
    return re.search(rf'class="[^"]*\b{cls}', html) is not None


def _unlock_report(css_rule: str | None, canvas_w: int, canvas_h: int) -> list[str]:
    return [
        f"{prop}:{value}px"
        for prop, value in (("width", canvas_w), ("height", canvas_h))
        if css_rule is None or not _locked(css_rule, prop, value)
    ]


def _section_pairs(html: str) -> set[str]:
    """手机内屏状态节点集合：`<section data-screen=.. data-state=..>`。"""
    pairs: set[str] = set()
    for tag in SECTION_TAG_RE.findall(html):
        s = re.search(r'data-screen="([^"]+)"', tag)
        t = re.search(r'data-state="([^"]+)"', tag)
        if s and t:
            pairs.add(f"{s.group(1)}@{t.group(1)}")
    return pairs


def _check_manifest(manifest: dict, gotos: list[str], sections: set[str]) -> list[str]:
    """interaction manifest 静态契约：悬空/覆盖/可达 + HTML↔manifest 同步。"""
    problems: list[str] = []
    screens = manifest.get("screens")
    routes = manifest.get("routes")
    if not isinstance(screens, list) or not screens:
        return ["manifest screens 缺失或为空（需 [{id,name,module,states:[…]}]）"]
    if not isinstance(routes, list) or not routes:
        problems.append("manifest routes 缺失或为空")

    nodes: set[str] = set()
    screen_ids: set[str] = set()
    first_state: dict[str, str] = {}
    for s in screens:
        sid, states = s.get("id"), s.get("states")
        if not sid or not isinstance(states, list) or not states:
            problems.append(f"screen 声明不完整 {s!r}（需 id + 非空 states）")
            continue
        screen_ids.add(sid)
        first_state[sid] = states[0]
        nodes.update(f"{sid}@{st}" for st in states)

    goto_nodes: set[str] = set()
    for g in gotos:
        if "@" in g:
            if g in nodes:
                goto_nodes.add(g)
            else:
                problems.append(f"侧栏页面项 data-goto 指向未声明目标: {g!r}")
        elif g in screen_ids:
            goto_nodes.add(f"{g}@{first_state[g]}")  # 裸屏 id = 进该屏首个状态
        else:
            problems.append(f"侧栏页面项 data-goto 指向未声明目标: {g!r}")
    for sid in sorted(screen_ids - {g.split("@")[0] for g in gotos}):
        problems.append(f"侧栏缺少页面项（data-goto）: {sid}")

    if not routes:
        return problems

    entry = (manifest.get("meta") or {}).get("entry")
    if entry not in nodes:
        problems.append(f"meta.entry 悬空或缺失: {entry!r}")

    edges: dict[str, set[str]] = {}
    tagged = {t: False for t in COVERAGE_TAGS}
    for i, r in enumerate(routes):
        rid = r.get("id", f"#{i}")
        for role in ("from", "to"):
            if r.get(role) not in nodes:
                problems.append(f"路由 {rid} {role} 悬空目标: {r.get(role)!r}")
        if r.get("from") in nodes and r.get("to") in nodes:
            edges.setdefault(r["from"], set()).add(r["to"])
        if r.get("event") not in VALID_EVENTS:
            problems.append(f"路由 {rid} event 非法: {r.get('event')!r}（∈ {VALID_EVENTS}）")
        for t in r.get("tags", []):
            if t in tagged:
                tagged[t] = True
    missing_tags = [t for t, hit in tagged.items() if not hit]
    if missing_tags:
        problems.append(
            "五类覆盖缺失: " + "/".join(missing_tags)
            + "（routes tags 需 main/success/cancel/error/recover 各≥1）"
        )

    if entry in nodes:
        seen = {entry}
        stack = [entry]
        while stack:
            for nxt in edges.get(stack.pop(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        success = {
            r["to"] for r in routes
            if "success" in r.get("tags", []) and r.get("to") in nodes
        }
        if not success & seen:
            problems.append("起点 entry 经手机内路由到 success 出口不可达")
        # 侧栏是浏览入口：data-goto 目标视为可达（裸屏 id 折算为 <screen>@default，
        # 非默认态需显式 data-goto="screen@state" 或手机内路由可达）
        dead = sorted(n for n in nodes if n not in seen and n not in goto_nodes)
        if dead:
            problems.append("从 entry 不可达的屏状态（路由与侧栏均到不了）: " + ", ".join(dead))

    html_only = sections - nodes
    if html_only:
        problems.append("HTML section 节点未在 manifest 声明: " + ", ".join(sorted(html_only)))
    manifest_only = nodes - sections
    if manifest_only:
        problems.append("manifest 节点缺 HTML section（data-screen/data-state）: "
                        + ", ".join(sorted(manifest_only)))
    return problems


def check_file(path: Path, canvas_w: int, canvas_h: int, platform: str = "mobile") -> list[str]:
    problems: list[str] = []
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"[IO] {path.name}: {exc}"]

    # TAG — balance of container tags
    for tag in ("div", "span"):
        opens = len(re.findall(rf"<{tag}[\s>]", html))
        closes = len(re.findall(rf"</{tag}>", html))
        if opens != closes:
            problems.append(f"[TAG] {path.name}: <{tag}> {opens} open / {closes} close")

    css = re.search(r"<style>(.*?)</style>", html, re.DOTALL)

    # CANVAS — only applies when the file defines screen frames (.frame rules)
    if css and re.search(r"\.frame\s*\{", css.group(1)):
        rule = re.search(r"\.frame\s*\{[^}]*\}", css.group(1))
        missing = _unlock_report(rule.group(0) if rule else None, canvas_w, canvas_h)
        if missing:
            problems.append(f"[CANVAS] {path.name}: .frame 未锁定 " + " / ".join(missing))

    # PROTOTYPE — stage-8 interactive-prototype contract
    is_workbench = _has_element(html, WORKBENCH_MARKER)
    if platform == "mobile" and path.name.startswith("08-prototype") and not is_workbench:
        problems.append(
            f"[WORKBENCH] {path.name}: --platform mobile 时最终原型必须是工作台"
            f"（缺 {WORKBENCH_MARKER} 外壳元素；桌面/Web 项目请传 --platform desktop/web）"
        )
    if is_workbench:
        for cls, desc in (
            ("workbench-sidebar", "左侧页面列表 .workbench-sidebar"),
            ("device-caption", "手机下方说明 .device-caption"),
        ):
            if not _has_element(html, cls):
                problems.append(f"[WORKBENCH] {path.name}: 工作台缺{desc}")
        if not css:
            problems.append(f"[WORKBENCH] {path.name}: 缺 <style>（.device-frame 规则）")
        else:
            rule = re.search(r"\.device-frame\s*\{[^}]*\}", css.group(1))
            missing = _unlock_report(rule.group(0) if rule else None, canvas_w, canvas_h)
            if missing:
                problems.append(f"[CANVAS] {path.name}: .device-frame 未锁定 " + " / ".join(missing))
        m = MANIFEST_RE.search(html)
        if not m:
            problems.append(f"[MANIFEST] {path.name}: 缺 interaction manifest"
                            '（<script type="application/json" id="interaction-manifest">）')
        else:
            try:
                manifest = json.loads(m.group(1))
            except json.JSONDecodeError as exc:
                problems.append(f"[MANIFEST] {path.name}: JSON 解析失败: {exc}")
            else:
                for p in _check_manifest(manifest, GOTO_RE.findall(html), _section_pairs(html)):
                    problems.append(f"[MANIFEST] {path.name}: {p}")

    # DEPS — self-containment for every artifact (no external http(s) resources)
    ext = EXTERNAL_RES_RE.search(html)
    if ext:
        problems.append(f"[DEPS] {path.name}: 引用外部资源（须内联自包含）: {ext.group(0)[:60]!r}")

    # COPY — banned words over visible text (case-insensitive for latin)
    text = strip_to_text(html)
    low = text.lower()
    for word in BANNED_COPY:
        if word.lower() in low:
            problems.append(f"[COPY] {path.name}: 命中负面清单 '{word}'")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="HTML artifact gate: tag/canvas/copy/prototype")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--canvas-width", type=int, default=390, help="项目目标画布宽（默认 390=手机）")
    parser.add_argument("--canvas-height", type=int, default=844, help="项目目标画布高（默认 844=手机）")
    parser.add_argument("--platform", choices=("mobile", "desktop", "web"), default="mobile",
                        help="tokens 目标端（默认 mobile：08-prototype.html 必须为工作台）")
    args = parser.parse_args()

    files: list[Path] = []
    for p in args.paths:
        if p.is_dir():
            files += sorted(p.glob("*.html"))
        elif p.is_file() and p.suffix == ".html":
            files.append(p)
        else:
            print(f"[IO] 跳过非 HTML 路径: {p}", file=sys.stderr)
    if not files:
        print("[IO] 没有 HTML 文件可检查", file=sys.stderr)
        return 2

    all_problems: list[str] = []
    for f in files:
        all_problems += check_file(f, args.canvas_width, args.canvas_height, args.platform)

    for line in all_problems:
        print(line)
    status = "PASS" if not all_problems else "FAIL"
    print(f"— {status}: {len(files)} 个文件，{len(all_problems)} 处问题")
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main())
