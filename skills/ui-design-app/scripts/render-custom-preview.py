#!/usr/bin/env python3
"""Render a compact custom Finder or Linear preview from a JSON information architecture."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent


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
    if style not in {"finder", "linear"}:
        parser.error("JSON field 'style' must be finder or linear")
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
    content = finder_markup(data, css_urls) if style == "finder" else linear_markup(data, css_urls)
    theme = "light" if data.get("theme") == "light" else "dark"
    document = f"""<!doctype html><html lang="zh-CN" data-theme="{theme}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>定制 UI 预览</title>
<style>*{{box-sizing:border-box}}html,body{{margin:0;min-height:100%;background:#111216}}.preview{{width:min(1100px,94vw);height:680px;margin:30px auto;overflow:hidden;border-radius:12px;box-shadow:0 24px 70px rgba(0,0,0,.45)}}.preview-body{{display:flex;height:calc(100% - 48px)}}.preview-body .sidebar-dock{{width:260px}}.preview-main{{flex:1;min-width:0;padding:0 10px 10px}}.preview-list{{min-height:520px;border:1px solid var(--finder-divider);border-radius:10px;padding:8px}}.linear-head{{padding:24px;border-bottom:1px solid var(--ln-border)}}.linear-head h1{{font-size:16px}}.linear-head>div{{display:flex;gap:8px}}.linear-list{{padding:12px 16px}}</style></head><body>{content}</body></html>"""

    destination = Path(args.output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    print(json.dumps({"output": str(destination), "style": style}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
