#!/usr/bin/env python3
"""Render a compact custom style preview from a JSON information architecture."""

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
}


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


STYLE_MARKUP = {
    "finder": finder_markup,
    "linear": linear_markup,
    "things": things_markup,
    "geist": geist_markup,
    "figma": figma_markup,
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
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="JSON file with style/title/navigation/toolbar/rows")
    source_group.add_argument("--spec-json", help="Inline JSON with style/title/navigation/toolbar/rows")
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

    assets = SKILL_ROOT / "assets" / "styles" / style
    if args.base_url:
        base = args.base_url.rstrip("/")
        css_urls = (
            f"{base}/assets/styles/{style}/tokens.css",
            f"{base}/assets/styles/{style}/{style}-ui.css",
        )
    else:
        css_urls = ((assets / "tokens.css").as_uri(), (assets / f"{style}-ui.css").as_uri())
    content = STYLE_MARKUP[style](data, css_urls)
    theme = data.get("theme") if data.get("theme") in {"light", "dark"} else STYLE_DEFAULT_THEME[style]
    document = f"""<!doctype html><html lang="zh-CN" data-theme="{theme}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>定制 UI 预览</title>
<style>{COMMON_PREVIEW_CSS}{STYLE_PREVIEW_CSS[style]}</style></head><body>{content}</body></html>"""

    destination = Path(args.output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    print(json.dumps({"output": str(destination), "style": style, "theme": theme}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
