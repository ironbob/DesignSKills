#!/usr/bin/env python3
"""Validate the pre-code decision between direct UI editing and arch-first."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _report import Report, emit  # noqa: E402

MODES = {"create", "repair"}
SIZES = {"small", "medium", "large"}
LOGIC_CHANGES = {"none", "local_wiring", "business_logic"}
PATHS = {"direct_ui", "arch_first"}
RISK_KEYS = {
    "navigation_change",
    "state_ownership_change",
    "data_flow_change",
    "api_or_persistence_change",
    "new_dependency",
    "cross_layer_change",
    "shared_component_or_token_change",
    "multiple_screens",
    "architecture_role_change",
}


def _text(item: dict[str, Any], key: str) -> bool:
    return isinstance(item.get(key), str) and bool(item[key].strip())


def _expected_size(files: int) -> str:
    if files <= 3:
        return "small"
    if files <= 7:
        return "medium"
    return "large"


def expected_path(document: dict[str, Any]) -> str | None:
    meta = document.get("meta")
    estimate = document.get("estimate")
    risks = document.get("risk_flags")
    if not isinstance(meta, dict) or not isinstance(estimate, dict) or not isinstance(risks, dict):
        return None
    if meta.get("user_forced_arch_first") is True:
        return "arch_first"
    if set(risks) != RISK_KEYS or any(risks.get(key) is not False for key in RISK_KEYS):
        return "arch_first"
    logic = estimate.get("logic_change")
    ui_only = estimate.get("ui_only")
    size = estimate.get("change_size")
    if logic not in {"none", "local_wiring"}:
        return "arch_first"
    if ui_only is True and logic != "none":
        return "arch_first"
    return "direct_ui" if size == "small" or ui_only is True else "arch_first"


def validate(document: dict[str, Any]) -> Report:
    report = Report()
    meta = document.get("meta")
    meta_ok = (
        isinstance(meta, dict)
        and meta.get("mode") in MODES
        and _text(meta, "target_screen")
        and meta.get("stage") == "pre_code"
        and isinstance(meta.get("revision"), int)
        and meta["revision"] > 0
        and isinstance(meta.get("user_forced_arch_first"), bool)
    )
    report.add("CPA.meta", "ERROR", meta_ok, "meta 须含 mode/target_screen/stage=pre_code/正整数 revision/user_forced_arch_first" if not meta_ok else "评估 meta 完整")
    if isinstance(meta, dict) and meta.get("user_forced_arch_first") is True:
        report.add("CPA.force", "ERROR", _text(meta, "force_evidence"), "用户强制 arch-first 时须记录 force_evidence" if not _text(meta, "force_evidence") else "用户强制证据已记录")

    estimate = document.get("estimate")
    estimate_ok = (
        isinstance(estimate, dict)
        and isinstance(estimate.get("production_files"), int)
        and estimate["production_files"] > 0
        and estimate.get("change_size") in SIZES
        and isinstance(estimate.get("ui_only"), bool)
        and estimate.get("logic_change") in LOGIC_CHANGES
    )
    report.add("CPA.estimate", "ERROR", estimate_ok, "estimate 须含正整数 production_files、合法 change_size/ui_only/logic_change" if not estimate_ok else "改动量估算完整")
    if estimate_ok:
        expected_size = _expected_size(estimate["production_files"])
        report.add("CPA.size", "ERROR", estimate["change_size"] == expected_size, f"production_files={estimate['production_files']} 时 change_size 应为 {expected_size}" if estimate["change_size"] != expected_size else "文件数与改动档位一致")
        ui_logic_ok = not estimate["ui_only"] or estimate["logic_change"] == "none"
        report.add("CPA.ui_logic", "ERROR", ui_logic_ok, "ui_only=true 时 logic_change 必须为 none" if not ui_logic_ok else "纯 UI 与逻辑声明一致")

    evidence = document.get("evidence")
    evidence_ok = isinstance(evidence, list) and bool(evidence) and all(isinstance(value, str) and value.strip() for value in evidence)
    report.add("CPA.evidence", "ERROR", evidence_ok, "evidence 须为非空文字数组，列出已检查文件/审计项" if not evidence_ok else f"评估证据={len(evidence)} 条")

    risks = document.get("risk_flags")
    risks_ok = isinstance(risks, dict) and set(risks) == RISK_KEYS and all(isinstance(risks[key], bool) for key in RISK_KEYS)
    report.add("CPA.risks", "ERROR", risks_ok, f"risk_flags 必须完整包含 {sorted(RISK_KEYS)} 且值为 boolean" if not risks_ok else "风险项完整")

    decision = document.get("decision")
    decision_ok = isinstance(decision, dict) and decision.get("path") in PATHS and _text(decision, "rationale")
    report.add("CPA.decision", "ERROR", decision_ok, "decision 须含 direct_ui|arch_first path 与 rationale" if not decision_ok else f"编码路径={decision['path']}")
    expected = expected_path(document)
    parity_ok = decision_ok and expected is not None and decision["path"] == expected
    report.add("CPA.path", "ERROR", parity_ok, f"按风险与规模计算应走 {expected!r}，实际 {decision.get('path') if isinstance(decision, dict) else None!r}" if not parity_ok else f"编码路径判定正确：{expected}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-code change-size and architecture-path gate")
    parser.add_argument("assessment", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.assessment.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 change assessment：{exc}", file=sys.stderr)
        return 2
    if not isinstance(document, dict):
        print("change assessment 顶层须为对象", file=sys.stderr)
        return 2
    return emit(validate(document), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
