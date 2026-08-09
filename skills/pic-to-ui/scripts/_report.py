#!/usr/bin/env python3
"""Shared Report class for pic-to-ui gate scripts.

Conventions mirror ``skills/interaction-prototype/scripts/validate_page_plan.py``:
- severity ERROR blocks the exit code; WARNING / ADVISORY are informational.
- ``print()`` renders a human-readable report; ``--json`` emits ``{"ok", "items"}``.
- the caller returns ``0 if report.ok() else 1``.

Only the deterministic checks (the things a rule can decide) set ERROR. Visual
diff and self-check are advisory by design (see references/validation-rules.md),
so they never go through this gate — they live in report.md.
"""
from __future__ import annotations

import json
from typing import Any

GLYPH = {"ERROR": "🔴", "WARNING": "🟡", "ADVISORY": "🟢"}
_ORDER = ["ERROR", "WARNING", "ADVISORY"]


class Report:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, code: str, severity: str, ok: bool, detail: str) -> None:
        if severity not in GLYPH:
            raise ValueError(f"bad severity {severity!r}")
        self.items.append(
            {"code": code, "severity": severity, "ok": bool(ok), "detail": detail}
        )

    def ok(self) -> bool:
        """True iff no ERROR check failed."""
        return not any(it["severity"] == "ERROR" and not it["ok"] for it in self.items)

    def print(self) -> None:
        failures = [it for it in self.items if not it["ok"]]
        passes = [it for it in self.items if it["ok"]]
        if failures:
            print("未通过项：")
            for it in sorted(failures, key=lambda i: _ORDER.index(i["severity"])):
                print(
                    f"  {GLYPH[it['severity']]} [{it['severity']}] {it['code']}: {it['detail']}"
                )
        print(f"\n通过 {len(passes)} 项，未通过 {len(failures)} 项。")
        print(f"判定：{'✅ 通过（无 ERROR）' if self.ok() else '❌ 未通过（存在 ERROR）'}")

    def as_json(self) -> dict[str, Any]:
        return {"ok": self.ok(), "items": self.items}


def emit(report: Report, want_json: bool) -> int:
    if want_json:
        print(json.dumps(report.as_json(), ensure_ascii=False, indent=2))
    else:
        report.print()
    return 0 if report.ok() else 1
