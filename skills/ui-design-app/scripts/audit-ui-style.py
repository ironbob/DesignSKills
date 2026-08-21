#!/usr/bin/env python3
"""Audit UI style risks and build a deterministic static UI-surface inventory."""

from __future__ import annotations

import argparse
import bisect
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_TEXT_EXTENSIONS = {
    # Web styles and templates.
    ".css", ".pcss", ".postcss", ".scss", ".sass", ".less", ".styl",
    ".html", ".htm", ".xhtml", ".vue", ".svelte", ".astro", ".mdx",
    ".jsx", ".tsx", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts",
    ".pug", ".jade", ".hbs", ".handlebars", ".ejs", ".erb", ".php",
    ".twig", ".liquid", ".njk", ".nunjucks", ".razor", ".cshtml",
    ".jsp", ".jspx", ".ftl", ".vm", ".mustache",
    # Native and cross-platform UI sources.
    ".swift", ".m", ".mm", ".h", ".qml", ".dart", ".kt", ".kts",
    ".java", ".xml", ".xaml", ".storyboard", ".xib",
}
CONDITIONAL_CONFIG_EXTENSIONS = {".json", ".json5", ".yaml", ".yml", ".toml", ".plist"}
POTENTIAL_UI_EXTENSIONS = {
    ".cs", ".fs", ".fsx", ".lua", ".gd", ".rs", ".ui", ".ux",
}
NON_UI_RESOURCE_EXTENSIONS = {
    ".md", ".mdown", ".markdown", ".txt", ".rst", ".adoc",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico",
    ".mp3", ".mp4", ".mov", ".wav", ".m4a", ".pdf",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".zip", ".gz", ".tar", ".lock", ".map",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "dist", "build", "coverage",
    "vendor", ".next", ".nuxt", ".svelte-kit", ".astro", ".cache",
    "__pycache__", "Pods", "DerivedData", ".gradle", ".idea", ".dart_tool",
}
UI_PATH_HINTS = {
    "app", "apps", "page", "pages", "route", "routes", "screen", "screens",
    "view", "views", "component", "components", "widget", "widgets", "ui",
    "layout", "layouts", "style", "styles", "theme", "themes", "frontend",
    "token", "tokens", "design", "navigation", "menu",
}
NON_UI_CODE_DIRS = {"scripts", "script", "tests", "test", "docs", "documentation"}
MAX_FILE_BYTES = 2_000_000
COMMON_STATES = ("hover", "active", "disabled", "focus_visible")

BASE_RULES = {
    "hardcoded_color": re.compile(r"(?<![-\w])#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl)a?\([^)]*\)"),
    "important": re.compile(r"!important\b"),
    "background_shorthand": re.compile(r"(?m)^\s*background\s*:"),
    "gradient": re.compile(r"(?:linear|radial|conic)-gradient\("),
    "backdrop_filter": re.compile(r"(?:-webkit-)?backdrop-filter\s*:"),
    "overflow_hidden": re.compile(r"overflow(?:-[xy])?\s*:\s*hidden"),
    "fixed_containing_block": re.compile(
        r"(?:transform|filter|perspective|container-type|contain|will-change)\s*:\s*[^;]+"
    ),
}
STATE_PATTERNS = {
    "hover": re.compile(r":hover\b|\bonHover\b|\bhovered\b", re.IGNORECASE),
    "active": re.compile(r":active\b|\bpressed\b|\bisPressed\b", re.IGNORECASE),
    "disabled": re.compile(r":disabled\b|\[aria-disabled|\bdisabled\s*[=:]", re.IGNORECASE),
    "focus_visible": re.compile(r":focus-visible\b|\bfocusVisible\b|\bfocused\b", re.IGNORECASE),
    "selected": re.compile(r"aria-selected|\bselected\s*[=:]|\bisSelected\b", re.IGNORECASE),
    "checked": re.compile(r"aria-checked|\bchecked\s*[=:]|\bisChecked\b", re.IGNORECASE),
    "expanded_open": re.compile(r"aria-expanded|\b(?:open|expanded)\s*[=:]|\bisOpen\b", re.IGNORECASE),
    "loading": re.compile(r"\b(?:loading|isLoading|pending|skeleton)\b", re.IGNORECASE),
    "empty": re.compile(r"\b(?:empty|emptyState|noResults|noData)\b", re.IGNORECASE),
    "error": re.compile(r"\b(?:error|hasError|invalid|aria-invalid)\b", re.IGNORECASE),
    "offline": re.compile(r"\boffline\b|navigator\.onLine", re.IGNORECASE),
    "permission": re.compile(r"\b(?:permission|unauthorized|forbidden|accessDenied)\b", re.IGNORECASE),
}
STYLE_TOKEN_PREFIX = {
    "finder": "--finder-",
    "linear": "--ln-",
    "things": "--th-",
    "geist": "--ge-",
    "figma": "--fig-",
    "codex": "--cx-",
}
STYLE_RADIUS_LIMIT = {"linear": 8.0, "geist": 10.0}

SEMANTIC_ELEMENT_PATTERN = re.compile(
    r"<\s*(button|input|select|textarea|a|nav|main|aside|header|footer|form|dialog|table|details|summary)\b",
    re.IGNORECASE,
)
ARIA_ROLE_PATTERN = re.compile(r"\brole\s*=\s*[{'\"]+([a-z-]+)", re.IGNORECASE)
NATIVE_ELEMENT_PATTERNS = {
    "native:button": re.compile(
        r"\b(?:Button|UIButton|NSButton|ElevatedButton|FilledButton|TextButton|IconButton)\s*(?:\(|\{)"
    ),
    "native:input": re.compile(
        r"\b(?:TextField|SecureField|UITextField|NSTextField|EditText|TextArea)\s*(?:\(|\{)"
    ),
    "native:toggle": re.compile(
        r"\b(?:Toggle|Switch|Checkbox|CheckBox|UISwitch|NSSwitch)\s*(?:\(|\{)"
    ),
    "native:select": re.compile(r"\b(?:Picker|DropdownButton|ComboBox|Spinner)\s*(?:\(|\{)"),
    "native:list": re.compile(
        r"\b(?:List|Table|ListView|RecyclerView|LazyColumn|LazyRow|UICollectionView|NSTableView)\s*(?:\(|\{)"
    ),
    "native:menu": re.compile(r"\b(?:Menu|DropdownMenu|UIMenu|NSMenu)\s*(?:\(|\{)"),
    "native:link": re.compile(r"\b(?:NavigationLink|Link)\s*(?:\(|\{)"),
}
CUSTOM_ELEMENT_PATTERN = re.compile(r"<\s*([A-Z][A-Za-z0-9_]*)\b")
COMPONENT_PATTERNS = (
    re.compile(r"\b(?:export\s+)?(?:default\s+)?function\s+([A-Z][A-Za-z0-9_]*)\b"),
    re.compile(r"\b(?:export\s+)?(?:const|let|var)\s+([A-Z][A-Za-z0-9_]*)\s*(?::[^=]+)?=\s*(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"),
    re.compile(r"\bclass\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+(?:React\.)?(?:Component|PureComponent|StatelessWidget|StatefulWidget)\b"),
    re.compile(r"\bstruct\s+([A-Z][A-Za-z0-9_]*)\s*:\s*View\b"),
    re.compile(r"@Composable\s+(?:public\s+|private\s+|internal\s+)?fun\s+([A-Z][A-Za-z0-9_]*)\b"),
)
ROUTE_PATTERNS = (
    re.compile(r"<Route\b[^>]*\bpath\s*=\s*[{'\"]+([^'\"}\s]+)", re.IGNORECASE),
    re.compile(r"\bpath\s*:\s*['\"](/[^'\"]*)['\"]"),
    re.compile(r"\b(?:route|path)\s*\(\s*['\"](/[^'\"]*)['\"]", re.IGNORECASE),
)
OVERLAY_PATTERNS = {
    "dialog": re.compile(r"<\s*dialog\b|\brole\s*=\s*[{'\"]+dialog|\bDialog\b"),
    "modal": re.compile(r"\bModal\b|\bmodal\b"),
    "popover": re.compile(r"\bPopover\b|\bpopover\b"),
    "menu": re.compile(r"\bContextMenu\b|\bDropdownMenu\b|\brole\s*=\s*[{'\"]+menu"),
    "drawer": re.compile(r"\bDrawer\b|\bSheet\b"),
    "tooltip": re.compile(r"\bTooltip\b|\brole\s*=\s*[{'\"]+tooltip"),
    "toast": re.compile(r"\bToast\b|\btoast\b"),
    "portal": re.compile(r"createPortal\b|\bPortal\b|\bTeleport\b"),
}
THEME_PATTERNS = {
    "light": re.compile(r"data-theme\s*=\s*['\"]light|\.light\b|\blightTheme\b", re.IGNORECASE),
    "dark": re.compile(r"data-theme\s*=\s*['\"]dark|\.dark\b|prefers-color-scheme\s*:\s*dark|\bdarkTheme\b", re.IGNORECASE),
    "system": re.compile(r"prefers-color-scheme|\bsystemTheme\b|\btheme\s*===?\s*['\"]system", re.IGNORECASE),
}
BREAKPOINT_PATTERN = re.compile(r"@media\s*\(([^)]+(?:width|orientation)[^)]*)\)", re.IGNORECASE)


@dataclass(frozen=True)
class Discovery:
    files: tuple[Path, ...]
    skipped: dict[str, dict[str, object]]


def add_example(bucket: dict[str, object], value: str, limit: int) -> None:
    bucket["count"] = int(bucket.get("count", 0)) + 1
    examples = bucket.setdefault("examples", [])
    if len(examples) < limit and value not in examples:
        examples.append(value)


def looks_like_ui(path: Path) -> bool:
    lower_parts = {part.lower() for part in path.parts}
    if lower_parts & NON_UI_CODE_DIRS:
        return False
    stem = path.stem.lower()
    return bool(lower_parts & UI_PATH_HINTS) or any(
        hint in stem for hint in ("page", "screen", "view", "component", "widget", "layout", "theme", "style")
    )


def discover_files(
    root: Path,
    extensions: set[str],
    max_file_bytes: int,
    max_examples: int,
) -> Discovery:
    files: list[Path] = []
    skipped: dict[str, dict[str, object]] = defaultdict(lambda: {"count": 0, "examples": []})

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(dirpath)
        kept_dirs: list[str] = []
        for dirname in sorted(dirnames):
            candidate = base / dirname
            relative = candidate.relative_to(root).as_posix()
            if dirname in SKIP_DIRS:
                add_example(skipped["excluded_directory"], relative, max_examples)
            elif candidate.is_symlink():
                add_example(skipped["symlink_directory"], relative, max_examples)
            else:
                kept_dirs.append(dirname)
        dirnames[:] = kept_dirs

        for filename in sorted(filenames):
            path = base / filename
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                add_example(skipped["symlink_file"], relative, max_examples)
                continue
            suffix = path.suffix.lower()
            if suffix in CONDITIONAL_CONFIG_EXTENSIONS and looks_like_ui(path.relative_to(root)):
                pass
            elif suffix not in extensions:
                if suffix in NON_UI_RESOURCE_EXTENSIONS or filename == ".DS_Store":
                    continue
                if suffix in POTENTIAL_UI_EXTENSIONS or looks_like_ui(path.relative_to(root)):
                    add_example(skipped["unsupported_ui_extension"], relative, max_examples)
                continue
            try:
                size = path.stat().st_size
            except OSError:
                add_example(skipped["stat_error"], relative, max_examples)
                continue
            if size > max_file_bytes:
                add_example(skipped["large_file"], relative, max_examples)
                continue
            files.append(path)

    return Discovery(tuple(sorted(files, key=lambda path: path.relative_to(root).as_posix())), dict(skipped))


def newline_offsets(text: str) -> list[int]:
    return [match.start() for match in re.finditer("\n", text)]


def line_number(offsets: list[int], offset: int) -> int:
    return bisect.bisect_right(offsets, offset) + 1


def line_column(offsets: list[int], offset: int) -> tuple[int, int]:
    line = line_number(offsets, offset)
    line_start = offsets[line - 2] + 1 if line > 1 else 0
    return line, offset - line_start + 1


def convention_routes(relative: Path) -> set[str]:
    parts = list(relative.parts)
    routes: set[str] = set()
    filename = relative.name
    stem = relative.stem

    if "app" in parts and stem in {"page", "+page"}:
        index = parts.index("app")
        segments = [part for part in parts[index + 1 : -1] if not (part.startswith("(") and part.endswith(")"))]
        routes.add("/" + "/".join(segments))
    if "pages" in parts and stem not in {"_app", "_document", "_error"}:
        index = parts.index("pages")
        segments = parts[index + 1 : -1] + [stem]
        if segments and segments[-1] == "index":
            segments.pop()
        routes.add("/" + "/".join(segments))
    if "routes" in parts and filename.startswith("+page"):
        index = parts.index("routes")
        segments = [part for part in parts[index + 1 : -1] if not (part.startswith("(") and part.endswith(")"))]
        routes.add("/" + "/".join(segments))
    if relative.suffix.lower() in {".html", ".htm"}:
        segments = list(relative.with_suffix("").parts)
        if segments and segments[-1] == "index":
            segments.pop()
        routes.add("/" + "/".join(segments))
    return {route.rstrip("/") or "/" for route in routes}


def scan_file(
    path: Path,
    root: Path,
    style: str,
    token_prefix: str,
    max_examples: int,
) -> dict[str, object]:
    relative_path = path.relative_to(root)
    relative = relative_path.as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"relative": relative, "error": "decode_error"}
    except OSError:
        return {"relative": relative, "error": "read_error"}

    offsets = newline_offsets(text)
    lines = text.splitlines()
    audit_counts: Counter[str] = Counter()
    audit_examples: dict[str, list[str]] = defaultdict(list)
    state_counts: Counter[str] = Counter()
    state_sources: dict[str, list[str]] = defaultdict(list)

    for state, pattern in STATE_PATTERNS.items():
        matches = list(pattern.finditer(text))
        state_counts[state] = len(matches)
        if matches:
            state_sources[state].append(relative)

    is_token_file = path.name == "tokens.css"
    for rule, pattern in BASE_RULES.items():
        for match in pattern.finditer(text):
            number = line_number(offsets, match.start())
            matched_line = lines[number - 1] if lines else ""
            if rule == "hardcoded_color" and is_token_file:
                continue
            if rule == "important" and (
                "animation-duration" in matched_line or "transition-duration" in matched_line
            ):
                continue
            audit_counts[rule] += 1
            if len(audit_examples[rule]) < max_examples:
                audit_examples[rule].append(f"{relative}:{number}")

    radius_limit = STYLE_RADIUS_LIMIT.get(style)
    if radius_limit is not None:
        radius_rule = f"{style}_large_radius"
        for match in re.finditer(r"border-radius\s*:\s*(\d+(?:\.\d+)?)px", text):
            number = line_number(offsets, match.start())
            matched_line = lines[number - 1] if lines else ""
            if float(match.group(1)) > radius_limit and "scrollbar" not in matched_line:
                audit_counts[radius_rule] += 1
                if len(audit_examples[radius_rule]) < max_examples:
                    audit_examples[radius_rule].append(f"{relative}:{number}")

    components: set[str] = set()
    for pattern in COMPONENT_PATTERNS:
        components.update(pattern.findall(text))
    if path.suffix.lower() in {".vue", ".svelte", ".astro", ".qml"}:
        components.add(path.stem)
    custom_elements = CUSTOM_ELEMENT_PATTERN.findall(text)
    components.update(custom_elements)

    routes = convention_routes(relative_path)
    for pattern in ROUTE_PATTERNS:
        routes.update(pattern.findall(text))

    element_instances: list[dict[str, object]] = []
    for pattern, prefix in ((SEMANTIC_ELEMENT_PATTERN, ""), (ARIA_ROLE_PATTERN, "role:")):
        for match in pattern.finditer(text):
            line, column = line_column(offsets, match.start())
            element_instances.append({
                "kind": f"{prefix}{match.group(1).lower()}",
                "line": line,
                "column": column,
            })
    for kind, pattern in NATIVE_ELEMENT_PATTERNS.items():
        for match in pattern.finditer(text):
            line, column = line_column(offsets, match.start())
            element_instances.append({"kind": kind, "line": line, "column": column})
    if path.suffix.lower() in {".jsx", ".tsx", ".mdx"} and not components and element_instances:
        components.add(path.stem)
    semantic_elements = Counter(str(item["kind"]) for item in element_instances)

    overlays = {name for name, pattern in OVERLAY_PATTERNS.items() if pattern.search(text)}
    themes = {name for name, pattern in THEME_PATTERNS.items() if pattern.search(text)}
    breakpoints = {" ".join(value.split()) for value in BREAKPOINT_PATTERN.findall(text)}
    visual_declarations = len(re.findall(
        r"\b(?:color|background(?:-color)?|border(?:-radius|-color)?|box-shadow|font(?:-size|-family|-weight)?|padding|margin|gap)\s*:",
        text,
        re.IGNORECASE,
    ))

    return {
        "relative": relative,
        "error": None,
        "token_uses": text.count(f"var({token_prefix}"),
        "audit_counts": dict(audit_counts),
        "audit_examples": dict(audit_examples),
        "state_counts": dict(state_counts),
        "state_sources": dict(state_sources),
        "components": sorted(components),
        "routes": sorted(routes),
        "elements": dict(semantic_elements),
        "element_instances": element_instances,
        "overlays": sorted(overlays),
        "themes": sorted(themes),
        "breakpoints": sorted(breakpoints),
        "visual_declarations": visual_declarations,
    }


def sourced_items(mapping: dict[str, set[str]], max_examples: int) -> list[dict[str, object]]:
    return [
        {"id": item, "sources": sorted(sources)[:max_examples], "source_count": len(sources)}
        for item, sources in sorted(mapping.items())
    ]


def blocking_unknowns(skipped: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    blockers = []
    for kind in (
        "unsupported_ui_extension", "large_file", "symlink_directory", "symlink_file",
        "stat_error", "decode_error", "read_error",
    ):
        payload = skipped.get(kind)
        if payload and int(payload.get("count", 0)):
            blockers.append({"kind": kind, "count": payload["count"], "examples": payload.get("examples", [])})
    blockers.append({
        "kind": "runtime_inventory_unverified",
        "count": 1,
        "examples": ["conditional UI, portals, permissions, data states, focus order and visual rendering require runtime evidence"],
    })
    return blockers


def build_report(
    root: Path,
    style: str,
    discovery: Discovery,
    results: Iterable[dict[str, object]],
    workers_used: int,
    max_examples: int,
) -> dict[str, object]:
    findings_counts: Counter[str] = Counter()
    findings_examples: dict[str, list[str]] = defaultdict(list)
    state_counts: Counter[str] = Counter({name: 0 for name in STATE_PATTERNS})
    state_sources: dict[str, set[str]] = defaultdict(set)
    component_sources: dict[str, set[str]] = defaultdict(set)
    route_sources: dict[str, set[str]] = defaultdict(set)
    overlay_sources: dict[str, set[str]] = defaultdict(set)
    theme_sources: dict[str, set[str]] = defaultdict(set)
    breakpoint_sources: dict[str, set[str]] = defaultdict(set)
    element_counts: Counter[str] = Counter()
    element_sources: dict[str, set[str]] = defaultdict(set)
    element_instances: list[dict[str, object]] = []
    source_files: list[dict[str, object]] = []
    token_uses = 0
    files_scanned = 0
    skipped = {key: {"count": value["count"], "examples": list(value.get("examples", []))} for key, value in discovery.skipped.items()}

    for result in results:
        relative = str(result["relative"])
        error = result.get("error")
        if error:
            bucket = skipped.setdefault(str(error), {"count": 0, "examples": []})
            add_example(bucket, relative, max_examples)
            continue
        files_scanned += 1
        token_uses += int(result.get("token_uses", 0))

        active_states = sorted(
            state for state, count in dict(result.get("state_counts", {})).items() if int(count)
        )
        source_files.append({
            "id": relative,
            "components": list(result.get("components", [])),
            "routes": list(result.get("routes", [])),
            "interactive_elements": sorted(dict(result.get("elements", {}))),
            "overlays": list(result.get("overlays", [])),
            "states": active_states,
            "themes": list(result.get("themes", [])),
            "breakpoints": list(result.get("breakpoints", [])),
            "visual_declarations": int(result.get("visual_declarations", 0)),
        })

        for rule, count in dict(result.get("audit_counts", {})).items():
            findings_counts[rule] += int(count)
        for rule, examples in dict(result.get("audit_examples", {})).items():
            for example in examples:
                if len(findings_examples[rule]) < max_examples and example not in findings_examples[rule]:
                    findings_examples[rule].append(example)
        for state, count in dict(result.get("state_counts", {})).items():
            state_counts[state] += int(count)
            if count:
                state_sources[state].add(relative)
        for component in result.get("components", []):
            component_sources[str(component)].add(relative)
        for route in result.get("routes", []):
            route_sources[str(route)].add(relative)
        for overlay in result.get("overlays", []):
            overlay_sources[str(overlay)].add(relative)
        for theme in result.get("themes", []):
            theme_sources[str(theme)].add(relative)
        for breakpoint in result.get("breakpoints", []):
            breakpoint_sources[str(breakpoint)].add(relative)
        for element, count in dict(result.get("elements", {})).items():
            element_counts[element] += int(count)
            element_sources[element].add(relative)
        for instance in result.get("element_instances", []):
            kind = str(instance["kind"])
            line = int(instance["line"])
            column = int(instance["column"])
            element_instances.append({
                "id": f"{relative}:{line}:{column}:{kind}",
                "kind": kind,
                "source": relative,
                "line": line,
                "column": column,
            })

    candidate_count = len(discovery.files)
    static_ratio = round(files_scanned / candidate_count, 4) if candidate_count else 1.0
    blockers = blocking_unknowns(skipped)
    static_blockers = [item for item in blockers if item["kind"] != "runtime_inventory_unverified"]
    status = "static_incomplete" if static_blockers else "static_complete_runtime_unverified"

    findings = {
        rule: {"count": count, "examples": findings_examples.get(rule, [])}
        for rule, count in sorted(findings_counts.items())
        if count
    }
    component_instances = [
        {"id": f"{source}::{name}", "name": name, "source": source}
        for name, sources in sorted(component_sources.items())
        for source in sorted(sources)
    ]
    inventory = {
        "source_files": {"count": len(source_files), "items": source_files},
        "routes": {"count": len(route_sources), "items": sourced_items(route_sources, max_examples)},
        "components": {
            "count": len(component_instances),
            "unique_name_count": len(component_sources),
            "items": component_instances,
        },
        "interactive_elements": {
            "count": len(element_instances),
            "items": sorted(element_instances, key=lambda item: str(item["id"])),
            "kinds": [
                {
                    "id": element,
                    "occurrences": element_counts[element],
                    "sources": sorted(element_sources[element])[:max_examples],
                    "source_count": len(element_sources[element]),
                }
                for element in sorted(element_counts)
            ],
        },
        "overlays": {"count": len(overlay_sources), "items": sourced_items(overlay_sources, max_examples)},
        "states": {
            "counts": dict(sorted(state_counts.items())),
            "missing_common_states": [state for state in COMMON_STATES if not state_counts[state]],
            "sources": {state: sorted(sources)[:max_examples] for state, sources in sorted(state_sources.items())},
        },
        "themes": {"count": len(theme_sources), "items": sourced_items(theme_sources, max_examples)},
        "breakpoints": {"count": len(breakpoint_sources), "items": sourced_items(breakpoint_sources, max_examples)},
    }

    return {
        "project": str(root),
        "style": style,
        # Compatibility fields retained for existing consumers.
        "files_scanned": files_scanned,
        "semantic_token_uses": token_uses,
        "state_selector_counts": {state: state_counts[state] for state in COMMON_STATES},
        "missing_state_selectors": [state for state in COMMON_STATES if not state_counts[state]],
        "findings": findings,
        # New bounded inventory and coverage contract.
        "scan": {
            "mode": "parallel" if workers_used > 1 else "serial",
            "workers_used": workers_used,
            "candidate_files": candidate_count,
            "files_scanned": files_scanned,
            "static_file_coverage": static_ratio,
            "skipped": dict(sorted(skipped.items())),
        },
        "inventory": inventory,
        "coverage": {
            "status": status,
            "claim_full_coverage": False,
            "runtime_required": True,
            "blockers": blockers,
        },
    }


def normalize_extensions(extra: list[str]) -> set[str]:
    extensions = set(DEFAULT_TEXT_EXTENSIONS)
    for value in extra:
        cleaned = value.strip().lower()
        if not cleaned:
            continue
        extensions.add(cleaned if cleaned.startswith(".") else f".{cleaned}")
    return extensions


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--style", choices=tuple(STYLE_TOKEN_PREFIX), required=True)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--max-examples", type=int, default=12)
    parser.add_argument("--max-file-bytes", type=int, default=MAX_FILE_BYTES)
    parser.add_argument("--workers", type=int, default=0, help="0=auto, 1=serial")
    parser.add_argument("--include-extension", action="append", default=[], help="Extra text extension")
    parser.add_argument("--inventory-output", help="Optional path for the inventory JSON only")
    parser.add_argument("--fail-on-unknowns", action="store_true", help="Exit 2 when static/runtime blockers remain")
    parser.add_argument("--profile", action="store_true", help="Print elapsed milliseconds to stderr")
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"project is not a directory: {root}")
    if args.max_examples < 1 or args.max_file_bytes < 1 or args.workers < 0:
        parser.error("max-examples/max-file-bytes must be positive and workers must be >= 0")

    started = time.perf_counter()
    extensions = normalize_extensions(args.include_extension)
    discovery = discover_files(root, extensions, args.max_file_bytes, args.max_examples)
    auto_workers = min(32, (os.cpu_count() or 1) + 4)
    requested_workers = args.workers or auto_workers
    workers_used = max(1, min(requested_workers, len(discovery.files) or 1))
    scanner = lambda path: scan_file(
        path, root, args.style, STYLE_TOKEN_PREFIX[args.style], args.max_examples
    )
    if workers_used == 1:
        results = [scanner(path) for path in discovery.files]
    else:
        with ThreadPoolExecutor(max_workers=workers_used, thread_name_prefix="ui-audit") as executor:
            results = list(executor.map(scanner, discovery.files))

    report = build_report(root, args.style, discovery, results, workers_used, args.max_examples)
    if args.inventory_output:
        write_json(Path(args.inventory_output).expanduser().resolve(), report["inventory"])

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        scan = report["scan"]
        inventory = report["inventory"]
        print(
            f"Style audit: {args.style} · {scan['files_scanned']}/{scan['candidate_files']} files · "
            f"{scan['workers_used']} workers · {report['semantic_token_uses']} semantic-token uses"
        )
        print(
            "- inventory: "
            f"{inventory['routes']['count']} routes, {inventory['components']['count']} components, "
            f"{inventory['interactive_elements']['count']} interactive elements, "
            f"{inventory['overlays']['count']} overlay kinds"
        )
        for rule, payload in report["findings"].items():
            print(f"- {rule}: {payload['count']} ({', '.join(payload['examples'])})")
        if report["missing_state_selectors"]:
            print(f"- missing common states: {', '.join(report['missing_state_selectors'])}")
        print(
            f"- coverage: {report['coverage']['status']} · full-coverage claim is blocked until runtime evidence is merged"
        )
    if args.profile:
        print(f"audit_elapsed_ms={round((time.perf_counter() - started) * 1000, 2)}", file=sys.stderr)
    if args.fail_on_unknowns and report["coverage"]["blockers"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
