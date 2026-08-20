#!/usr/bin/env python3
"""Validate ui-design-app style-pack contracts, variables, docs, and demos."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_REFERENCES = ("tokens.md", "materials.md", "components.md", "patterns.md")
STYLE_ID = re.compile(r"^[a-z0-9-]+$")
CUSTOM_PROPERTY = re.compile(r"(--[A-Za-z0-9-]+)\s*:\s*([^;}{]+)")
VAR_USE = re.compile(r"var\(\s*(--[A-Za-z0-9-]+)")
TOKEN_ROW = re.compile(
    r"^\|\s*`(?P<name>--[\w-]+)`\s*\|\s*`(?P<light>[^`]+)`\s*\|\s*`(?P<dark>[^`]+)`",
    re.MULTILINE,
)
REQUIRED_USED = {
    "finder": {
        "--finder-selection",
        "--finder-control",
        "--finder-control-strong",
        "--finder-row-hover",
        "--finder-selection-bg",
        "--finder-inactive-sel",
    },
    "linear": {"--ln-accent", "--ln-hover", "--ln-active", "--ln-selected", "--ln-border"},
    "things": {"--th-accent", "--th-hover", "--th-active", "--th-selected", "--th-border"},
    "geist": {"--ge-accent", "--ge-hover", "--ge-active", "--ge-selected", "--ge-border"},
    "figma": {"--fig-accent", "--fig-hover", "--fig-active", "--fig-selected", "--fig-border"},
}


class DemoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.buttons: list[dict[str, object]] = []
        self._button: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        values = dict(attrs)
        if tag == "link" and values.get("href"):
            self.links.append(values["href"])
        if tag == "button":
            self._button = {"attrs": values, "text": ""}
            self.buttons.append(self._button)

    def handle_data(self, data: str) -> None:
        if self._button is not None:
            self._button["text"] = str(self._button["text"]) + data

    def handle_endtag(self, tag: str) -> None:
        if tag == "button":
            self._button = None


def normalize(value: str) -> str:
    compact = re.sub(r"\s+", "", value).lower()
    return re.sub(r"(?<!\d)\.(\d+)", r"0.\1", compact)


def theme_maps(css: str) -> tuple[dict[str, str], dict[str, str]]:
    blocks = re.findall(r"([^{}]+)\{([^{}]*)\}", css, re.DOTALL)
    dark: dict[str, str] = {}
    light: dict[str, str] = {}
    for selector, body in blocks:
        declarations = dict(CUSTOM_PROPERTY.findall(body))
        if not declarations:
            continue
        if ":root" in selector or "data-theme='dark'" in selector or 'data-theme="dark"' in selector:
            dark.update(declarations)
        if "data-theme='light'" in selector or 'data-theme="light"' in selector:
            light.update(declarations)
    return dark, light


def validate_style(style: str) -> dict[str, object]:
    if not STYLE_ID.fullmatch(style):
        return {"style": style, "errors": [f"invalid style id: {style}"], "warnings": []}
    refs = SKILL_ROOT / "references" / "styles" / style
    assets = SKILL_ROOT / "assets" / "styles" / style
    errors: list[str] = []
    warnings: list[str] = []

    for name in REQUIRED_REFERENCES:
        if not (refs / name).is_file():
            errors.append(f"missing reference: {refs / name}")
    for name in ("tokens.css", f"{style}-ui.css", "demo.html"):
        if not (assets / name).is_file():
            errors.append(f"missing asset: {assets / name}")
    if errors:
        return {"style": style, "errors": errors, "warnings": warnings}

    token_css = (assets / "tokens.css").read_text(encoding="utf-8")
    component_css = (assets / f"{style}-ui.css").read_text(encoding="utf-8")
    demo_html = (assets / "demo.html").read_text(encoding="utf-8")
    defined = set(name for name, _ in CUSTOM_PROPERTY.findall(token_css))
    used = set(VAR_USE.findall(token_css + component_css + demo_html))
    undefined = sorted(used - defined)
    if undefined:
        errors.append(f"undefined custom properties: {', '.join(undefined)}")
    missing_critical_usage = sorted((REQUIRED_USED.get(style, set()) & defined) - used)
    if missing_critical_usage:
        warnings.append(f"critical state tokens are not consumed: {', '.join(missing_critical_usage)}")

    dark, light = theme_maps(token_css)
    theme_tokens = {name for name in dark if not name.startswith("--z-")}
    missing_light = sorted(name for name in theme_tokens if name not in light)
    if missing_light:
        warnings.append(f"dark tokens inherited without explicit light override: {', '.join(missing_light)}")

    token_doc = (refs / "tokens.md").read_text(encoding="utf-8")
    for match in TOKEN_ROW.finditer(token_doc):
        name, light_doc, dark_doc = match.group("name", "light", "dark")
        if name not in defined:
            errors.append(f"documented token is not defined in CSS: {name}")
            continue
        if dark_doc not in {"同左", "—", "-"} and name in dark and normalize(dark_doc) != normalize(dark[name]):
            errors.append(f"dark token drift for {name}: docs={dark_doc}, css={dark[name].strip()}")
        if light_doc not in {"同左", "—", "-"} and name in light and normalize(light_doc) != normalize(light[name]):
            errors.append(f"light token drift for {name}: docs={light_doc}, css={light[name].strip()}")

    parser = DemoParser()
    parser.feed(demo_html)
    for href in parser.links:
        if href.startswith(("http://", "https://", "//")):
            errors.append(f"demo has network stylesheet: {href}")
        elif not (assets / href).resolve().is_file():
            errors.append(f"demo stylesheet not found: {href}")
    for index, button in enumerate(parser.buttons, start=1):
        attrs = button["attrs"]
        label = str(attrs.get("aria-label") or attrs.get("title") or button["text"]).strip()
        if not label:
            errors.append(f"demo button #{index} has no accessible name")
        if attrs.get("aria-checked") is not None and attrs.get("role") != "switch":
            errors.append(f"demo button #{index} uses aria-checked without role=switch")

    patterns = (refs / "patterns.md").read_text(encoding="utf-8")
    if re.search(r"<\s*768", patterns) and not re.search(r"max-width\s*:\s*76[78]px", component_css):
        warnings.append("patterns declare a <768 breakpoint but component CSS does not implement it")

    return {"style": style, "errors": errors, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("styles", nargs="*", help="Style ids; default validates every packaged style")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    styles = args.styles or sorted(
        path.name for path in (SKILL_ROOT / "assets" / "styles").iterdir() if path.is_dir()
    )
    reports = [validate_style(style) for style in styles]
    error_count = sum(len(report["errors"]) for report in reports)
    warning_count = sum(len(report["warnings"]) for report in reports)

    if args.format == "json":
        print(json.dumps({"errors": error_count, "warnings": warning_count, "styles": reports}, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(f"{report['style']}: {len(report['errors'])} errors, {len(report['warnings'])} warnings")
            for message in report["errors"]:
                print(f"  ERROR: {message}")
            for message in report["warnings"]:
                print(f"  WARN: {message}")
        print(f"Total: {error_count} errors, {warning_count} warnings")
    return 1 if error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
