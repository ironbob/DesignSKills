#!/usr/bin/env python3
"""Manifest-driven projection audit for epps-render (HTML / Android XML / Compose).

Verifies that each platform's rendered output is a strict projection of an EPPS
spec: same pages, same zone (id,kind) sequences, same assistive elements, and all
jump/host/behavior targets declared. The per-platform marker grammar is declared
in references/<platform>/projection.manifest.yaml (data-driven; adding a platform
needs no change here).

Reuses load_doc/normalize from skills/interaction-prototype/scripts/validate_epps.py.

Usage:
  python audit_projection.py <epps.json> <render-dir> [--platform html|xml|compose|all] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

# Reuse upstream validation loader (also gives us YAML/JSON parsing via load_doc).
SCRIPT_DIR = Path(__file__).resolve().parent
UPSTREAM = SCRIPT_DIR.parent.parent / "interaction-prototype" / "scripts"
sys.path.insert(0, str(UPSTREAM))
from validate_epps import load_doc, normalize  # type: ignore  # noqa: E402

REFERENCES = SCRIPT_DIR.parent / "references"

# platform -> (references dir, output file finder)
PLATFORMS = {
    "html": {"ref": "html", "find": lambda d: sorted((d / "html").glob("*.html"))},
    "xml": {"ref": "android-xml", "find": lambda d: sorted((d / "android-xml" / "layout").glob("*.xml"))},
    "compose": {"ref": "android-compose", "find": lambda d: sorted((d / "android-compose").rglob("*.kt"))},
}


# --------------------------------------------------------------------------- report
class Audit:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, ok: bool, code: str, message: str) -> None:
        self.items.append({"status": "PASS" if ok else "FAIL", "code": code, "message": message})

    def ok(self) -> bool:
        return all(i["status"] == "PASS" for i in self.items)

    def print(self) -> None:
        for i in self.items:
            print(("OK   " if i["status"] == "PASS" else "FAIL ") + f"{i['code']}: {i['message']}")


# --------------------------------------------------------------------------- spec helpers
def action_values_for_page(page: dict[str, Any]) -> set[str]:
    """All target/host/behavior values declared in the spec for a page (ported from audit_html_projection)."""
    values: set[str] = set()
    primary = page.get("primary_action") or {}
    if isinstance(primary, dict) and primary.get("target") is not None:
        values.add(str(primary.get("target")))
    for a in page.get("secondary_actions") or []:
        if isinstance(a, dict):
            if a.get("target") is not None:
                values.add(str(a.get("target")))
            elif a.get("behavior"):
                values.add(str(a.get("behavior")))
    for a in page.get("assistive_elements") or []:
        if isinstance(a, dict):
            if a.get("target") is not None:
                values.add(str(a.get("target")))
            elif a.get("behavior"):
                values.add(str(a.get("behavior")))
    nav = page.get("navigation") or {}
    if nav.get("back_target"):
        values.add(str(nav.get("back_target")))
    for j in page.get("jumps") or []:
        if isinstance(j, dict) and j.get("target") is not None:
            values.add(str(j.get("target")))
    return values


# --------------------------------------------------------------------------- dom_html extractor
def _parse_selector(sel: str) -> tuple[str | None, set[str], list[str]]:
    tag, classes, attrs = None, set(), []
    m = re.match(r"^([a-zA-Z][\w-]*)", sel)
    if m:
        tag = m.group(1)
    classes = set(re.findall(r"\.([a-zA-Z0-9_-]+)", sel))
    attrs = re.findall(r"\[([a-zA-Z0-9_-]+)\]", sel)
    return tag, classes, attrs


def _sel_match(sel: tuple[str | None, set[str], list[str]], tag: str, cls: set[str], attrs: dict[str, str]) -> bool:
    t, classes, present = sel
    if t is not None and tag != t:
        return False
    if not classes.issubset(cls):
        return False
    return all(a in attrs for a in present)


class HTMLExtractor(HTMLParser):
    def __init__(self, manifest: dict[str, Any]):
        super().__init__()
        self.m = manifest
        self.pages: dict[str, dict[str, Any]] = {}
        self.cur: str | None = None
        self.p_sel = _parse_selector(manifest["page"]["selector"])
        self.z_sel = _parse_selector(manifest["zone"]["selector"])
        self.a_sel = _parse_selector(manifest["assistive"]["selector"])
        self.p_attrs = manifest["page"].get("attrs", {})
        prim = manifest.get("primary")
        self.prim_sel = _parse_selector(prim["selector"]) if prim and prim.get("selector") else None

    def _page(self, pid: str) -> dict[str, Any]:
        return self.pages.setdefault(
            pid, {"level": "", "type": "", "tabbar": False, "zones": [], "assistive": [], "actions": [], "primaries": []}
        )

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = {k: ("" if v is None else v) for k, v in attrs}
        cls = set(d.get("class", "").split())
        if _sel_match(self.p_sel, tag, cls, d):
            self.cur = d.get(self.m["page"]["id_attr"], "")
            rec = self._page(self.cur)
            rec["level"] = d.get(self.p_attrs.get("level", ""), "")
            rec["type"] = d.get(self.p_attrs.get("type", ""), "")
            rec["tabbar"] = d.get(self.p_attrs.get("tabbar", "")) == "true"
        if self.cur and _sel_match(self.z_sel, tag, cls, d):
            self._page(self.cur)["zones"].append(
                {"id": d.get(self.m["zone"]["id_attr"], ""), "kind": d.get(self.m["zone"]["kind_attr"], "")}
            )
        if self.cur and _sel_match(self.a_sel, tag, cls, d):
            self._page(self.cur)["assistive"].append(
                {"id": d.get(self.m["assistive"]["id_attr"], ""), "kind": d.get(self.m["assistive"]["kind_attr"], "")}
            )
        if self.cur:
            if self.prim_sel and _sel_match(self.prim_sel, tag, cls, d):
                self._page(self.cur)["primaries"].append({"selector": self.m.get("primary", {}).get("selector", "")})
            for kind, attr in self.m["action"]["attrs"].items():
                if attr in d:
                    self._page(self.cur)["actions"].append({"kind": kind, "value": d[attr]})

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            self.cur = None


# --------------------------------------------------------------------------- dom_xml extractor
def extract_xml(files: list[Path], manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ns = "{" + manifest["namespace"] + "}"
    p, z, a = manifest["page"], manifest["zone"], manifest["assistive"]
    pm, zm, am = ns + p["match_attr"], ns + z["match_attr"], ns + a["match_attr"]
    act_attr = ns + manifest["action"]["attr"]
    prefixes = manifest["action"]["value_prefix"]
    prim_attr = ns + manifest["primary"]["match_attr"] if manifest.get("primary") else None
    pages: dict[str, dict[str, Any]] = {}
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        page_el = next((el for el in root.iter() if pm in el.attrib), None)
        if page_el is None:
            continue
        pid = page_el.attrib.get(pm, "")
        rec = pages.setdefault(
            pid, {"level": "", "type": "", "tabbar": False, "zones": [], "assistive": [], "actions": [], "primaries": []}
        )
        rec["level"] = page_el.attrib.get(ns + p["attrs"].get("level", ""), "")
        rec["type"] = page_el.attrib.get(ns + p["attrs"].get("type", ""), "")
        for el in page_el.iter():
            if el is page_el:
                continue
            if zm in el.attrib:
                rec["zones"].append({"id": el.attrib.get(zm, ""), "kind": el.attrib.get(ns + z["kind_attr"], "")})
            if am in el.attrib:
                rec["assistive"].append({"id": el.attrib.get(am, ""), "kind": el.attrib.get(ns + a["kind_attr"], "")})
            if prim_attr and prim_attr in el.attrib:
                rec["primaries"].append({"value": el.attrib.get(prim_attr, "")})
            if act_attr in el.attrib:
                val = el.attrib.get(act_attr, "")
                for kind, pfx in prefixes.items():
                    if val.startswith(pfx):
                        rec["actions"].append({"kind": kind, "value": val[len(pfx):]})
    return pages


# --------------------------------------------------------------------------- text_regex extractor
def extract_text(files: list[Path], manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pp = re.compile(manifest["page"]["pattern"])
    zp = re.compile(manifest["zone"]["pattern"])
    ap = re.compile(manifest["assistive"]["pattern"])
    xp = re.compile(manifest["action"]["pattern"])
    primp = re.compile(manifest["primary"]["pattern"]) if manifest.get("primary") else None
    xk = manifest["action"].get("kind_group", "kind")
    xv = manifest["action"].get("value_group", "value")
    pages: dict[str, dict[str, Any]] = {}
    cur: str | None = None
    for f in files:
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            if m := pp.search(line):
                g = m.groupdict()
                cur = g.get("id", "")
                pages.setdefault(
                    cur,
                    {"level": g.get("level", ""), "type": g.get("type", ""), "tabbar": False,
                     "zones": [], "assistive": [], "actions": [], "primaries": []},
                )
            elif cur and (m := zp.search(line)):
                g = m.groupdict()
                pages[cur]["zones"].append({"id": g.get("id", ""), "kind": g.get("kind", "")})
            elif cur and (m := ap.search(line)):
                g = m.groupdict()
                pages[cur]["assistive"].append({"id": g.get("id", ""), "kind": g.get("kind", "")})
            elif cur and primp and primp.search(line):
                pages[cur]["primaries"].append({"line": line.strip()})
            elif cur and (m := xp.search(line)):
                g = m.groupdict()
                pages[cur]["actions"].append({"kind": g.get(xk, ""), "value": g.get(xv, "")})
    return pages


EXTRACTORS = {"dom_html": None, "dom_xml": extract_xml, "text_regex": extract_text}  # dom_html set in run()


def extract(platform: str, manifest: dict[str, Any], files: list[Path]) -> dict[str, dict[str, Any]]:
    parse = manifest["parse"]
    if parse == "dom_html":
        parser = HTMLExtractor(manifest)
        for f in files:
            parser.feed(f.read_text(encoding="utf-8", errors="ignore"))
        return parser.pages
    if parse == "dom_xml":
        return extract_xml(files, manifest)
    if parse == "text_regex":
        return extract_text(files, manifest)
    raise SystemExit(f"unknown parse strategy: {parse}")


# --------------------------------------------------------------------------- compare
def compare(
    proto: dict[str, Any],
    pages: list[dict[str, Any]],
    extracted: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    audit: Audit,
    platform: str,
) -> None:
    page_by_id = {str(p.get("id")): p for p in pages if p.get("id")}
    page_ids = set(page_by_id)
    host_ids = {
        str(a.get("id")) for a in proto.get("host_anchors", []) or [] if isinstance(a, dict) and a.get("id")
    }
    ext_ids = set(extracted)
    audit.add(not (page_ids - ext_ids), f"{platform}.PAGE.present", f"missing pages: {sorted(page_ids - ext_ids)}")
    audit.add(not (ext_ids - page_ids), f"{platform}.PAGE.extra", f"extra pages: {sorted(ext_ids - page_ids)}")

    has_tabbar = "tabbar" in manifest.get("page", {}).get("attrs", {})
    for pid, page in page_by_id.items():
        ex = extracted.get(pid)
        if not ex:
            continue
        audit.add(ex["type"] == str(page.get("type")), f"{platform}.PAGE.type", f"{pid}: {ex['type']} vs {page.get('type')}")
        audit.add(ex["level"] == str(page.get("level")), f"{platform}.PAGE.level", f"{pid}: {ex['level']} vs {page.get('level')}")
        if has_tabbar:
            expected = (page.get("navigation") or {}).get("tab_bar") is True
            audit.add(ex["tabbar"] == expected, f"{platform}.PAGE.tabbar", f"{pid}: {ex['tabbar']} vs {expected}")

        spec_pairs = [(str(z.get("id")), str(z.get("kind"))) for z in (page.get("density") or {}).get("zones") or [] if isinstance(z, dict)]
        ex_pairs = [(z["id"], z["kind"]) for z in ex["zones"]]
        audit.add(spec_pairs == ex_pairs, f"{platform}.ZONE.projection", f"{pid}: {ex_pairs} vs {spec_pairs}")

        spec_apairs = [(str(z.get("id")), str(z.get("kind"))) for z in page.get("assistive_elements") or [] if isinstance(z, dict)]
        ex_apairs = [(z["id"], z["kind"]) for z in ex["assistive"]]
        audit.add(spec_apairs == ex_apairs, f"{platform}.ASSISTIVE.projection", f"{pid}: {ex_apairs} vs {spec_apairs}")

        allowed = action_values_for_page(page)
        unknown = []
        for ac in ex["actions"]:
            if ac["kind"] == "host":
                if ac["value"] not in host_ids:
                    unknown.append(f"host:{ac['value']}")
            elif ac["value"] not in allowed:
                unknown.append(f"{ac['kind']}:{ac['value']}")
        audit.add(not unknown, f"{platform}.ACTION.declared", f"{pid}: undeclared {unknown}")

        if manifest.get("primary"):
            nprim = len(ex.get("primaries", []))
            audit.add(nprim <= 1, f"{platform}.PRIMARY.unique",
                      f"{pid}: {nprim} primary marker(s) — at most 1 allowed per page")


def check_sample_state(files: list[Path], audit: Audit, platform: str) -> None:
    bad: list[str] = []
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.findall(r"\{\{[^}]+\}\}", txt):
            bad.append(f"{f.name}:{m}")
    audit.add(not bad, f"{platform}.SAMPLE_STATE.resolved", f"unresolved placeholders: {bad[:6]}")


# --------------------------------------------------------------------------- main
def run_platform(name: str, proto: dict[str, Any], pages: list[dict[str, Any]], out_dir: Path, audit: Audit) -> None:
    cfg = PLATFORMS[name]
    manifest_path = REFERENCES / cfg["ref"] / "projection.manifest.yaml"
    if not manifest_path.exists():
        audit.add(False, f"{name}.MANIFEST.present", f"missing {manifest_path}")
        return
    manifest = load_doc(manifest_path)
    files = cfg["find"](out_dir)
    audit.add(bool(files), f"{name}.FILES.present",
              f"{len(files)} output file(s) found" if files else f"no output files found for {name}")
    if not files:
        return
    extracted = extract(name, manifest, files)
    compare(proto, pages, extracted, manifest, audit, name)
    check_sample_state(files, audit, name)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit epps-render multi-platform output against an EPPS spec.")
    ap.add_argument("spec", type=Path, help="Path to epps.json/yaml/md")
    ap.add_argument("out_dir", type=Path, help="Render output dir (e.g. prototype/<date>-<theme>/render)")
    ap.add_argument("--platform", default="all", choices=["html", "xml", "compose", "all"])
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON report")
    args = ap.parse_args()

    try:
        proto, pages = normalize(load_doc(args.spec))
    except SystemExit as e:
        print(f"FAILED to load spec: {e}", file=sys.stderr)
        return 2

    targets = list(PLATFORMS) if args.platform == "all" else [args.platform]
    audit = Audit()
    for name in targets:
        run_platform(name, proto, pages, args.out_dir, audit)

    if args.json:
        print(json.dumps({"ok": audit.ok(), "items": audit.items}, ensure_ascii=False, indent=2))
    else:
        for name in targets:
            print(f"==== {name} ====")
        audit.print()
        print(f"\nRESULT: {'PASS' if audit.ok() else 'FAIL'} ({sum(1 for i in audit.items if i['status']=='PASS')}/{len(audit.items)} checks)")
    return 0 if audit.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())
