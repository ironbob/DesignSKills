#!/usr/bin/env python3
"""Generate an offline side-by-side comparison for packaged style demos."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
STYLE_ID = re.compile(r"^[a-z0-9-]+$")


def output_file(value: str) -> Path:
    target = Path(value).expanduser().resolve()
    return target if target.suffix.lower() == ".html" else target / "comparison.html"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("styles", nargs="+", help="Style ids to compare")
    parser.add_argument("--output", default="/tmp/ui-style-preview", help="Output directory or HTML file")
    parser.add_argument("--base-url", help="Optional HTTP URL for the skill root; defaults to file URLs")
    args = parser.parse_args()

    if len(args.styles) < 2:
        parser.error("provide at least two style ids")

    demos: list[tuple[str, Path]] = []
    for style in args.styles:
        if not STYLE_ID.fullmatch(style):
            parser.error(f"invalid style id: {style}")
        demo = SKILL_ROOT / "assets" / "styles" / style / "demo.html"
        if not demo.is_file():
            parser.error(f"unknown style or missing demo: {style}")
        demos.append((style, demo))

    demo_urls = [
        f"{args.base_url.rstrip('/')}/assets/styles/{style}/demo.html" if args.base_url else demo.as_uri()
        for style, demo in demos
    ]
    cards = "\n".join(
        f'''<section class="card">
  <header>{html.escape(style)}</header>
  <div class="frame"><iframe title="{html.escape(style)} 风格演示" src="{html.escape(demo_url, quote=True)}"></iframe></div>
</section>'''
        for (style, _), demo_url in zip(demos, demo_urls)
    )
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UI 风格并排对比</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; min-height: 100%; background: #111216; color: #f5f5f7;
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif; }}
  main {{ display: grid; grid-template-columns: repeat({len(demos)}, minmax(360px, 1fr));
    gap: 12px; min-height: 100vh; padding: 12px; }}
  .card {{ min-width: 0; overflow: hidden; border: 1px solid rgba(255,255,255,.12);
    border-radius: 12px; background: #1a1b20; }}
  header {{ height: 38px; display: flex; align-items: center; padding: 0 14px;
    border-bottom: 1px solid rgba(255,255,255,.1); font-size: 13px; font-weight: 600; }}
  .frame {{ height: calc(100vh - 64px); overflow: hidden; }}
  iframe {{ display: block; border: 0; background: white; transform-origin: top left; }}
  @media (max-width: 900px) {{ main {{ grid-template-columns: 1fr; }} .frame {{ height: 720px; }} }}
</style>
</head>
<body><main>{cards}</main>
<script>
  function fitFrames() {{
    document.querySelectorAll('.frame').forEach(frame => {{
      const scale = Math.min(1, frame.clientWidth / 1100);
      const iframe = frame.querySelector('iframe');
      iframe.style.width = `${{100 / scale}}%`;
      iframe.style.height = `${{frame.clientHeight / scale}}px`;
      iframe.style.transform = `scale(${{scale}})`;
    }});
  }}
  new ResizeObserver(fitFrames).observe(document.querySelector('main'));
  addEventListener('load', fitFrames);
</script></body>
</html>
"""

    destination = output_file(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    print(json.dumps({"output": str(destination), "styles": args.styles}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
