#!/usr/bin/env python3
"""Render a style preview from legacy lists or a preserved semantic region layout."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
# 各风格 preview 的默认主题（与 demo 人设一致：finder/linear 暗色默认，其余亮色默认）。
STYLE_DEFAULT_THEME = {
    "finder": "dark",
    "linear": "dark",
    "things": "light",
    "geist": "light",
    "figma": "light",
    "codex": "light",
}

POSITIONS = {"top", "left", "main", "right", "bottom"}


def items(values: list[str], class_name: str, tag: str = "div") -> str:
    return "\n".join(f'<{tag} class="{class_name}">{html.escape(str(value))}</{tag}>' for value in values)


def finder_markup(data: dict, css_urls: tuple[str, str]) -> str:
    title = html.escape(str(data.get("title", "应用预览")))
    navigation = items(data.get("navigation", []), "sidebar-item")
    toolbar = items(data.get("toolbar", []), "finder-pill-btn", "button")
    rows = items(data.get("rows", []), "finder-list-row")
    return f"""<link rel="stylesheet" href="{html.escape(css_urls[0], quote=True)}"><link rel="stylesheet" href="{html.escape(css_urls[1], quote=True)}">
<main class="finder-shell preview finder-preview">
  <header class="finder-window-titlebar"><strong>{title}</strong></header>
  <div class="preview-body">
    <aside class="sidebar-dock"><div class="finder-sidebar"><div class="finder-sidebar-scroll">{navigation}</div></div></aside>
    <section class="preview-main">
      <div class="finder-pane-toolbar"><div class="finder-toolbar-capsule">{toolbar}</div></div>
      <div class="preview-list">{rows}</div>
    </section>
  </div>
</main>"""


def linear_markup(data: dict, css_urls: tuple[str, str]) -> str:
    title = html.escape(str(data.get("title", "应用预览")))
    navigation = items(data.get("navigation", []), "ln-row")
    toolbar = items(data.get("toolbar", []), "ln-btn secondary", "button")
    rows = items(data.get("rows", []), "ln-row")
    return f"""<link rel="stylesheet" href="{html.escape(css_urls[0], quote=True)}"><link rel="stylesheet" href="{html.escape(css_urls[1], quote=True)}">
<main class="ln-shell preview"><div class="ln-app">
  <nav class="ln-rail"><strong>UI</strong></nav>
  <aside class="ln-sidebar">{navigation}</aside>
  <section class="ln-main"><header class="linear-head"><h1>{title}</h1><div>{toolbar}</div></header><div class="linear-list">{rows}</div></section>
</div></main>"""


def things_markup(data: dict, css_urls: tuple[str, str]) -> str:
    title = html.escape(str(data.get("title", "应用预览")))
    navigation = items(data.get("navigation", []), "th-nav-item")
    toolbar = items(data.get("toolbar", []), "th-btn", "button")
    rows = "\n".join(
        f'<div class="th-todo"><span class="th-todo-title">{html.escape(str(value))}</span></div>'
        for value in data.get("rows", [])
    )
    return f"""<link rel="stylesheet" href="{html.escape(css_urls[0], quote=True)}"><link rel="stylesheet" href="{html.escape(css_urls[1], quote=True)}">
<main class="th-shell preview th-preview"><div class="th-app">
  <aside class="th-sidebar">{navigation}</aside>
  <section class="th-content">
    <h1 class="th-page-title">{title}</h1>
    <div class="preview-toolbar">{toolbar}</div>
    <div class="preview-list">{rows}</div>
  </section>
</div></main>"""


def geist_markup(data: dict, css_urls: tuple[str, str]) -> str:
    title = html.escape(str(data.get("title", "应用预览")))
    navigation = items(data.get("navigation", []), "ge-nav-item")
    toolbar = items(data.get("toolbar", []), "ge-btn secondary", "button")
    rows = items(data.get("rows", []), "ge-table-row")
    return f"""<link rel="stylesheet" href="{html.escape(css_urls[0], quote=True)}"><link rel="stylesheet" href="{html.escape(css_urls[1], quote=True)}">
<main class="ge-shell preview ge-preview"><div class="ge-app">
  <aside class="ge-sidebar">{navigation}</aside>
  <section class="ge-main">
    <div class="ge-page-head"><div><h1 class="ge-page-title">{title}</h1></div><div class="ge-page-actions">{toolbar}</div></div>
    <div class="preview-list">{rows}</div>
  </section>
</div></main>"""


def figma_markup(data: dict, css_urls: tuple[str, str]) -> str:
    title = html.escape(str(data.get("title", "应用预览")))
    navigation = data.get("navigation", [])
    layers = "\n".join(
        f'<div class="fig-layer{" selected" if index == 0 else ""}">{html.escape(str(value))}</div>'
        for index, value in enumerate(navigation)
    )
    frames = "\n".join(
        '<div class="fig-frame{cls}">{text}{badge}</div>'.format(
            cls=" selected" if index == 0 else "",
            text=html.escape(str(value)),
            badge='<span class="fig-size-badge">W 240 H 120</span>' if index == 0 else "",
        )
        for index, value in enumerate(data.get("rows", []))
    )
    return f"""<link rel="stylesheet" href="{html.escape(css_urls[0], quote=True)}"><link rel="stylesheet" href="{html.escape(css_urls[1], quote=True)}">
<main class="fig-shell fig-workspace preview fig-preview">
  <div class="fig-panel fig-toolbar"><button class="fig-zoom" title="缩放">100%</button></div>
  <div class="fig-panel fig-layers"><div class="fig-layer-scroll">{layers}</div><div class="fig-layer-count">{len(navigation)} 个图层</div></div>
  <div class="fig-panel fig-props">
    <div class="fig-tabs"><button class="fig-tab active">设计</button><button class="fig-tab">原型</button><button class="fig-tab">检查</button></div>
    <div class="fig-props-scroll">
      <div class="fig-sec"><div class="fig-sec-title">{title}</div>
        <div class="fig-row">
          <label class="fig-num"><span class="fig-num-label">X</span><input value="0" aria-label="X 坐标"></label>
          <label class="fig-num"><span class="fig-num-label">Y</span><input value="0" aria-label="Y 坐标"></label>
        </div>
      </div>
    </div>
  </div>
  <div class="fig-canvas-area">{frames}</div>
</main>"""


def codex_markup(data: dict, css_urls: tuple[str, str]) -> str:
    title = html.escape(str(data.get("title", "应用预览")))
    navigation = items(data.get("navigation", []), "cx-row")
    toolbar = items(data.get("toolbar", []), "cx-quiet", "button")
    rows = items(data.get("rows", []), "cx-message")
    return f"""<link rel="stylesheet" href="{html.escape(css_urls[0], quote=True)}"><link rel="stylesheet" href="{html.escape(css_urls[1], quote=True)}">
<main class="cx-shell preview cx-preview"><div class="cx-app">
  <aside class="cx-sidebar"><div class="cx-side-head"><strong>项目</strong></div><div class="cx-tree">{navigation}</div></aside>
  <section class="cx-main"><header class="cx-topbar"><strong class="cx-title">{title}</strong><div>{toolbar}</div></header>
    <div class="cx-main-inner">{rows}<div class="cx-composer">继续处理这项任务…</div></div>
  </section>
</div></main>"""


STYLE_MARKUP = {
    "finder": finder_markup,
    "linear": linear_markup,
    "things": things_markup,
    "geist": geist_markup,
    "figma": figma_markup,
    "codex": codex_markup,
}

COMMON_PREVIEW_CSS = """*{box-sizing:border-box}html,body{margin:0;min-height:100%;background:#111216}
.preview{width:min(1100px,94vw);height:680px;margin:30px auto;overflow:hidden;border-radius:12px;box-shadow:0 24px 70px rgba(0,0,0,.45)}
.preview-toolbar{display:flex;gap:8px;margin:0 0 16px;flex-wrap:wrap}"""

STYLE_PREVIEW_CSS = {
    "finder": """.preview-body{display:flex;height:calc(100% - 48px)}
.preview-body .sidebar-dock{width:260px}
.preview-main{flex:1;min-width:0;padding:0 10px 10px}
.preview-list{min-height:520px;border:1px solid var(--finder-divider);border-radius:10px;padding:8px}""",
    "linear": """.linear-head{padding:24px;border-bottom:1px solid var(--ln-border)}
.linear-head h1{font-size:16px}
.linear-head>div{display:flex;gap:8px}
.linear-list{padding:12px 16px}""",
    "things": """.th-preview .th-content{padding:32px 36px}
.th-preview .preview-list{max-width:640px}
.th-preview .th-btn{height:32px}""",
    "geist": """.ge-preview .preview-list{padding:8px 24px 24px;max-width:720px}
.ge-preview .ge-table-row{border-bottom:1px solid var(--ge-border)}""",
    "figma": """.fig-preview .fig-canvas-area{flex-direction:column;gap:16px}
.fig-preview .fig-frame{display:flex;align-items:flex-end;justify-content:center;font-size:12px;color:var(--fig-text);padding:8px}""",
    "codex": """.cx-preview .cx-main-inner{max-width:720px;margin:0 auto;padding:28px 24px}
.cx-preview .cx-topbar>div{display:flex;gap:6px}.cx-preview .cx-composer{margin-top:24px}""",
}

STYLE_SEMANTIC_CSS = {
    "finder": "--pv-canvas:var(--finder-canvas);--pv-surface:var(--finder-chrome);--pv-elevated:var(--finder-popover-bg);--pv-border:var(--finder-divider);--pv-text:var(--finder-label);--pv-secondary:var(--finder-secondary-label);--pv-hover:var(--finder-row-hover);--pv-selected:var(--finder-control-strong);--pv-accent:var(--finder-selection);--pv-danger:var(--accent-red);--pv-radius:10px;--pv-row:30px",
    "linear": "--pv-canvas:var(--ln-canvas);--pv-surface:var(--ln-surface);--pv-elevated:var(--ln-elevated);--pv-border:var(--ln-border);--pv-text:var(--ln-text);--pv-secondary:var(--ln-text-secondary);--pv-hover:var(--ln-hover);--pv-selected:var(--ln-selected);--pv-accent:var(--ln-accent);--pv-danger:var(--ln-danger);--pv-radius:6px;--pv-row:28px",
    "things": "--pv-canvas:var(--th-canvas);--pv-surface:var(--th-sidebar);--pv-elevated:var(--th-elevated);--pv-border:var(--th-border);--pv-text:var(--th-text);--pv-secondary:var(--th-text-secondary);--pv-hover:var(--th-hover);--pv-selected:var(--th-selected);--pv-accent:var(--th-accent);--pv-danger:var(--th-area-red);--pv-radius:10px;--pv-row:42px",
    "geist": "--pv-canvas:var(--ge-canvas);--pv-surface:var(--ge-surface);--pv-elevated:var(--ge-elevated);--pv-border:var(--ge-border);--pv-text:var(--ge-text);--pv-secondary:var(--ge-text-secondary);--pv-hover:var(--ge-hover);--pv-selected:var(--ge-selected);--pv-accent:var(--ge-accent);--pv-danger:var(--ge-danger);--pv-radius:8px;--pv-row:38px",
    "figma": "--pv-canvas:var(--fig-canvas);--pv-surface:var(--fig-panel);--pv-elevated:var(--fig-overlay);--pv-border:var(--fig-border);--pv-text:var(--fig-text);--pv-secondary:var(--fig-text-secondary);--pv-hover:var(--fig-hover);--pv-selected:var(--fig-selected);--pv-accent:var(--fig-accent);--pv-danger:var(--fig-danger);--pv-radius:12px;--pv-row:28px",
    "codex": "--pv-canvas:var(--cx-canvas);--pv-surface:var(--cx-sidebar);--pv-elevated:var(--cx-surface);--pv-border:var(--cx-border);--pv-text:var(--cx-text);--pv-secondary:var(--cx-text-secondary);--pv-hover:var(--cx-hover);--pv-selected:var(--cx-selected);--pv-accent:var(--cx-accent);--pv-danger:var(--cx-danger);--pv-radius:12px;--pv-row:30px",
}

SEMANTIC_PREVIEW_CSS = """
.semantic-preview{position:relative;color:var(--pv-text);background:var(--pv-canvas);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.semantic-frame{height:100%;display:grid;grid-template-columns:var(--pv-left) minmax(0,1fr) var(--pv-right);grid-template-rows:auto minmax(0,1fr) auto;background:var(--pv-canvas)}
.semantic-top{grid-column:1/-1;grid-row:1;border-bottom:1px solid var(--pv-border)}
.semantic-left{grid-column:1;grid-row:2;background:var(--pv-surface);border-right:1px solid var(--pv-border)}
.semantic-main{grid-column:2;grid-row:2;background:var(--pv-canvas)}
.semantic-right{grid-column:3;grid-row:2;background:var(--pv-surface);border-left:1px solid var(--pv-border)}
.semantic-bottom{grid-column:1/-1;grid-row:3;border-top:1px solid var(--pv-border)}
.semantic-slot{min-width:0;min-height:0;overflow:auto;padding:10px;display:flex;flex-direction:column;gap:10px}
.semantic-main.semantic-slot{padding:18px}.semantic-region{min-width:0;border-radius:var(--pv-radius);color:var(--pv-text)}
.semantic-main .semantic-region[data-kind='card'],.semantic-main .semantic-region[data-kind='form'],.semantic-main .semantic-region[data-kind='inspector']{background:var(--pv-elevated);border:1px solid var(--pv-border);padding:14px}
.semantic-region-head{display:flex;align-items:center;gap:10px;min-height:32px;margin-bottom:8px}.semantic-region-title{font-size:13px;font-weight:600;flex:1}.semantic-kind{font-size:10px;color:var(--pv-secondary);text-transform:uppercase;letter-spacing:.04em}
.semantic-actions{display:flex;gap:6px}.semantic-action{min-height:28px;padding:0 10px;border:1px solid var(--pv-border);border-radius:calc(var(--pv-radius) - 2px);background:var(--pv-elevated);color:var(--pv-text)}
.semantic-list{display:flex;flex-direction:column;gap:2px}.semantic-item{min-height:var(--pv-row);display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:calc(var(--pv-radius) - 3px);font-size:13px}.semantic-item:hover{background:var(--pv-hover)}.semantic-item.is-selected{background:var(--pv-selected)}.semantic-item.is-disabled{opacity:.42}.semantic-item-meta{margin-left:auto;color:var(--pv-secondary);font-size:11px}.semantic-status{width:7px;height:7px;border-radius:50%;background:var(--pv-accent);flex:none}
.semantic-state{padding:12px;border:1px dashed var(--pv-border);border-radius:var(--pv-radius);color:var(--pv-secondary);font-size:12px}.semantic-state.is-error{color:var(--pv-danger)}
.semantic-state-strip{position:absolute;right:12px;bottom:10px;display:flex;gap:5px;z-index:5}.semantic-state-chip{padding:3px 7px;border-radius:999px;background:var(--pv-elevated);border:1px solid var(--pv-border);color:var(--pv-secondary);font-size:10px}
"""


def _number(value, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


def semantic_item_markup(value) -> str:
    if isinstance(value, dict):
        label = html.escape(str(value.get("label", value.get("title", "项目"))))
        meta = html.escape(str(value.get("meta", "")))
        classes = ["semantic-item"]
        if value.get("selected"):
            classes.append("is-selected")
        if value.get("disabled"):
            classes.append("is-disabled")
        status = '<span class="semantic-status" aria-hidden="true"></span>' if value.get("status") else ""
        meta_markup = f'<span class="semantic-item-meta">{meta}</span>' if meta else ""
        return f'<div class="{" ".join(classes)}">{status}<span>{label}</span>{meta_markup}</div>'
    return f'<div class="semantic-item"><span>{html.escape(str(value))}</span></div>'


def semantic_region_markup(region: dict) -> str:
    title = html.escape(str(region.get("title", region.get("id", "区域"))))
    kind = html.escape(str(region.get("kind", "content")))
    actions = region.get("actions", [])
    action_markup = "".join(
        f'<button class="semantic-action">{html.escape(str(action.get("label", "操作") if isinstance(action, dict) else action))}</button>'
        for action in actions
    )
    values = region.get("items", region.get("rows", []))
    list_markup = "".join(semantic_item_markup(value) for value in values)
    state = str(region.get("state", "default"))
    state_markup = ""
    if state in {"loading", "empty", "error", "disabled", "offline", "permission"}:
        label = region.get("stateLabel", {"loading": "正在加载…", "empty": "暂无内容", "error": "载入失败", "disabled": "当前不可用", "offline": "当前离线", "permission": "没有访问权限"}[state])
        state_markup = f'<div class="semantic-state is-{html.escape(state)}">{html.escape(str(label))}</div>'
    return f'''<section class="semantic-region" data-kind="{kind}" data-state="{html.escape(state)}">
      <header class="semantic-region-head"><strong class="semantic-region-title">{title}</strong><span class="semantic-kind">{kind}</span><div class="semantic-actions">{action_markup}</div></header>
      <div class="semantic-list">{list_markup}</div>{state_markup}
    </section>'''


def semantic_markup(data: dict, css_urls: tuple[str, str]) -> tuple[str, str]:
    regions = data["regions"]
    buckets = {position: [] for position in POSITIONS}
    for region in regions:
        position = region.get("position", "main")
        buckets[position].append(semantic_region_markup(region))
    left_width = _number(next((region.get("width") for region in regions if region.get("position") == "left"), 240), 240, 160, 480) if buckets["left"] else 0
    right_width = _number(next((region.get("width") for region in regions if region.get("position") == "right"), 280), 280, 180, 520) if buckets["right"] else 0
    viewport = data.get("viewport", {})
    width = _number(viewport.get("width"), 1100, 360, 1800)
    height = _number(viewport.get("height"), 680, 420, 1200)
    states = data.get("states", [])
    state_strip = "".join(f'<span class="semantic-state-chip">{html.escape(str(state))}</span>' for state in states)
    links = f'<link rel="stylesheet" href="{html.escape(css_urls[0], quote=True)}"><link rel="stylesheet" href="{html.escape(css_urls[1], quote=True)}">'
    style = f"width:min({width}px,94vw);height:{height}px;--pv-left:{left_width}px;--pv-right:{right_width}px;{STYLE_SEMANTIC_CSS[data['style']]}"
    slots = "".join(
        f'<div class="semantic-{position} semantic-slot">{"".join(buckets[position])}</div>'
        for position in ("top", "left", "main", "right", "bottom") if buckets[position]
    )
    preserve_layout = data.get("preserveLayout", True) is not False
    content = f'''{links}<main class="preview semantic-preview" data-preserve-layout="{str(preserve_layout).lower()}" style="{style}">
      <div class="semantic-frame">{slots}</div><div class="semantic-state-strip">{state_strip}</div>
    </main>'''
    return content, "preserved-regions" if preserve_layout else "custom-regions"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="JSON file with style and legacy lists or semantic regions")
    source_group.add_argument("--spec-json", help="Inline JSON with style and legacy lists or semantic regions")
    parser.add_argument("--output", default="/tmp/ui-style-preview/custom-preview.html")
    parser.add_argument("--base-url", help="Optional HTTP URL for the skill root; defaults to file URLs")
    args = parser.parse_args()

    if args.input:
        source = Path(args.input).expanduser().resolve()
        data = json.loads(source.read_text(encoding="utf-8"))
    else:
        data = json.loads(args.spec_json)
    style = data.get("style")
    if style not in STYLE_MARKUP:
        parser.error(f"JSON field 'style' must be one of: {', '.join(STYLE_MARKUP)}")
    for key in ("navigation", "toolbar", "rows"):
        if key in data and not isinstance(data[key], list):
            parser.error(f"JSON field '{key}' must be an array")
    if "regions" in data:
        if not isinstance(data["regions"], list) or not data["regions"]:
            parser.error("JSON field 'regions' must be a non-empty array")
        for index, region in enumerate(data["regions"], start=1):
            if not isinstance(region, dict):
                parser.error(f"region #{index} must be an object")
            if region.get("position", "main") not in POSITIONS:
                parser.error(f"region #{index} position must be one of: {', '.join(sorted(POSITIONS))}")
            for key in ("items", "rows", "actions"):
                if key in region and not isinstance(region[key], list):
                    parser.error(f"region #{index} field '{key}' must be an array")
    if "states" in data and not isinstance(data["states"], list):
        parser.error("JSON field 'states' must be an array")

    assets = SKILL_ROOT / "assets" / "styles" / style
    if args.base_url:
        base = args.base_url.rstrip("/")
        css_urls = (
            f"{base}/assets/styles/{style}/tokens.css",
            f"{base}/assets/styles/{style}/{style}-ui.css",
        )
    else:
        css_urls = ((assets / "tokens.css").as_uri(), (assets / f"{style}-ui.css").as_uri())
    if data.get("regions"):
        content, mode = semantic_markup(data, css_urls)
    else:
        content, mode = STYLE_MARKUP[style](data, css_urls), "legacy-lists"
    theme = data.get("theme") if data.get("theme") in {"light", "dark"} else STYLE_DEFAULT_THEME[style]
    document = f"""<!doctype html><html lang="zh-CN" data-theme="{theme}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>定制 UI 预览</title>
<style>{COMMON_PREVIEW_CSS}{STYLE_PREVIEW_CSS[style]}{SEMANTIC_PREVIEW_CSS}</style></head><body>{content}</body></html>"""

    destination = Path(args.output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    print(json.dumps({"output": str(destination), "style": style, "theme": theme, "mode": mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
