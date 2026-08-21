#!/usr/bin/env python3
"""Create a risk-sized design-contract scaffold after both user confirmations.

The scaffold is intentionally incomplete: Codex must replace empty design and
implementation fields before validation. Confirmation evidence is required so
this helper cannot be used to bypass the skill's interaction gates.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any


STACKS = ("JVM", "C++", "FastAPI+Vue", "Swift/iOS")
PROFILES = ("light", "standard", "high_risk")
CONSTRUCTION_PRINCIPLES = (
    "cc_class_contract",
    "cc_routine_quality",
    "cc_defensive_programming",
    "cc_pseudocode_programming_process",
    "cc_minimize_variable_scope",
    "cc_one_variable_one_purpose",
    "cc_simple_control_flow",
    "cc_design_for_test",
    "cc_refactor_safely",
)


def _candidate(index: int) -> dict[str, Any]:
    return {
        "id": f"ALT-{index}",
        "summary": "",
        "strengths": [],
        "weaknesses": [],
        "risks": [],
    }


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    candidate_count = 1 if args.profile == "light" else 2
    review_mode = {
        "light": "self",
        "standard": "independent",
        "high_risk": "user",
    }[args.profile]
    role_budget = 3 if args.profile == "light" else None
    contract: dict[str, Any] = {
        "contract_version": 2,
        "feature": args.feature,
        "title": args.title,
        "stack": args.stack,
        "analyzed_at": args.analyzed_at,
        "existing_alignment": {
            "recognized_style": "",
            "new_code_follows": "",
        },
        "guidance": {
            "primary_source": "Code Complete, Second Edition",
            "secondary_sources": ["repository conventions", "SOLID", "DDD", "layered architecture"],
            "priority_order": ["functional_correctness", "context_savings", "speed", "token_savings"],
        },
        "interaction_confirmation": {
            "proposal_revision": args.proposal_revision,
            "profile_selection": {
                "status": "user_selected",
                "selected_profile": args.profile,
                "source": "user_message",
                "evidence": args.profile_evidence,
            },
            "design_confirmation": {
                "status": "user_confirmed",
                "confirmed_candidate": args.candidate,
                "confirmed_revision": args.proposal_revision,
                "source": "later_user_message",
                "evidence": args.design_evidence,
            },
        },
        "design_decision": {
            "profile": args.profile,
            "quality_attributes": [],
            "candidates": [_candidate(i) for i in range(1, candidate_count + 1)],
            "selected_id": args.candidate,
            "selection_reason": "",
            "top_down_check": "",
            "bottom_up_check": "",
            "risk_spikes": ([{
                "question": "",
                "method": "",
                "result": "",
                "status": "inconclusive",
            }] if args.profile == "high_risk" else []),
            "review": {
                "mode": review_mode,
                "reviewer": "",
                "findings": "",
                "disposition": "",
            },
            "complexity_budget": {
                "recommended_max_roles": role_budget,
                "exception_reason": "",
            },
            "domain_role_decision": {
                "status": "",
                "reason": "",
            },
        },
        "roles": [],
        "interfaces": [],
        "design_contract_checks": [],
        "business_process": [],
        "traceability": [],
        "construction_review": {
            "items": [
                {"principle": principle, "status": "not_reviewed", "evidence": ""}
                for principle in CONSTRUCTION_PRINCIPLES
            ],
        },
        "logging_standard": {
            "library": "",
            "key_nodes_instrumented": [],
        },
        "verification": {
            "commands": [],
            "checks": [],
            "matrix": [],
            "unverified": [],
        },
        "summary": {
            "roles_count": 0,
            "interfaces_count": 0,
            "process_steps": 0,
            "verification_checks": 0,
            "layer_roles": 0,
            "domain_roles": 0,
        },
        "gate": {
            "architecture": "no-go",
            "logging": "no-go",
            "coverage": "no-go",
            "verification": "no-go",
            "verdict": "no-go",
            "issues": [{
                "gate": "verification",
                "severity": "critical",
                "role_or_step": "scaffold",
                "problem": "契约骨架尚未完成",
                "evidence": "完成代码、测试和校验后替换本项",
            }],
            "notes": "契约骨架尚未完成；不得声明可交付",
        },
        "open_questions": [],
    }
    if args.ui_framework:
        contract["ui_architecture"] = {
            "framework": args.ui_framework,
            "current_patterns": [],
            "target_patterns": [],
            "state_management": "",
            "view_model_policy": "not_used",
            "mvvm_suitability": "not_suitable",
            "migration_impact": "none",
            "impact_scope": [],
            "migration_confirmation": "not_required",
            "decision_reason": "",
        }
    return contract


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create an arch-first design-contract scaffold")
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--stack", required=True, choices=STACKS)
    parser.add_argument("--feature", required=True, help="kebab-case feature name")
    parser.add_argument("--title", required=True)
    parser.add_argument("--profile-evidence", required=True,
                        help="Accurate summary of the user's profile-selection message")
    parser.add_argument("--design-evidence", required=True,
                        help="Accurate summary of the later design-confirmation message")
    parser.add_argument("--proposal-revision", type=int, default=1)
    parser.add_argument("--candidate", default="ALT-1")
    parser.add_argument("--analyzed-at", default=date.today().isoformat())
    parser.add_argument("--ui-framework")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.feature):
        parser.error("--feature must be kebab-case")
    if args.proposal_revision < 1:
        parser.error("--proposal-revision must be positive")
    if not re.fullmatch(r"ALT-\d+", args.candidate):
        parser.error("--candidate must match ALT-<n>")
    if args.output.exists() and not args.force:
        parser.error(f"output exists: {args.output}; pass --force to overwrite")
    return args


def main() -> int:
    args = parse_args()
    contract = build_contract(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"created {args.output} ({args.profile}, {args.stack}); scaffold remains no-go until completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
