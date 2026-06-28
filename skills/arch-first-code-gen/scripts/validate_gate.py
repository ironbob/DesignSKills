#!/usr/bin/env python3
"""Module E advisory self-check runner for arch-first-code-gen.

This is an evidence aid, not a CI-style hard gate. It independently recomputes
the three structural checks from real files (not from the contract's self-claim),
so it catches stale or over-optimistic self-assessment. Final delivery judgment
still belongs to the architecture/code-design principle review.

Reads: design-contract.json (manifest) + <feature>-arch.md (render) + repo root
        (for file existence). File paths in the contract are repo-root-relative.

  G-ARCH  架构门: every role's code_units file EXISTS (role↔code coverage);
          every depends_on resolves to a declared role id. A role with zero
          existing code files ⇒ critical.
  G-LOG   日志门: per-stack log-keyword coverage. A code unit with zero log
          calls ⇒ minor; logging = no-go when zero-log ratio > (1-ratio)
          (default covered ratio < 0.6). Honest structural proxy (PRD §6).
  G-COV   覆盖门: each business_process step's code_refs files EXIST, roles are
          valid, doc_ref present; AND contract↔doc cross-check — every contract
          role name appears in the doc 角色职责清单 table; frontmatter
          roles_count/process_steps/verdict consistent with the contract.

Recomputed verdict = go iff all three structural checks go. This script exits
non-zero only for invocation/parse errors; a recomputed no-go is printed as
advisory evidence for the agent to review. Semantic items (is a responsibility
*truly* single?) are NOT machine-checkable — register in gate.notes / 已知缺口,
never fake-verified.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

STACK_LOG_RE = {
    "JVM": re.compile(r"\b(?:log|logger|LOGGER|log_)\s*\."),
    "C++": re.compile(r"spdlog::"),
    "FastAPI+Vue": re.compile(r"\b(?:logger|log|logging)\s*(?:\.|::)"),
}


class Issues:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, gate: str, severity: str, role_or_step: str, problem: str, evidence: str) -> None:
        self.items.append({
            "gate": gate, "severity": severity, "role_or_step": role_or_step,
            "problem": problem, "evidence": evidence,
        })


def _nonempty(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _file_exists(rel: str, root: Path) -> tuple[bool, Path]:
    """rel may carry a trailing :method — split it off for existence check."""
    path_part = rel.split(":", 1)[0]
    p = (root / path_part).resolve() if not Path(path_part).is_absolute() else Path(path_part)
    try:
        return p.exists(), p
    except OSError:
        return False, p


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}, text
    raw, body = m.group(1), text[m.end():]
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, body


def extract_doc_roles(body: str) -> set[str]:
    """Role names from the 角色职责清单 table (first cell of each data row)."""
    # find the 角色职责 section
    secs = re.split(r"\n(?=#{2,6}\s+)", body)
    table_lines: list[str] = []
    in_role_sec = False
    for blk in secs:
        if "角色职责" in blk.split("\n", 1)[0]:
            in_role_sec = True
            table_lines = [ln for ln in blk.splitlines() if ln.lstrip().startswith("|")]
            break
    if not in_role_sec:
        # fallback: scan whole body for the first table with 角色 nearby
        table_lines = [ln for ln in body.splitlines() if ln.lstrip().startswith("|") and "角色" in body]
    names: set[str] = set()
    for ln in table_lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        # skip header / separator rows
        if set(first) <= set("-: "):
            continue
        if first in ("角色", "Role", ""):
            continue
        names.add(first)
    return names


def run(contract: dict, doc_text: str, root: Path, log_ratio: float) -> dict:
    issues = Issues()
    stack = contract.get("stack", "")
    roles = contract.get("roles") or []
    bps = contract.get("business_process") or []
    id_set = {r.get("id") for r in roles if isinstance(r, dict)}
    name_set = {r.get("name") for r in roles if isinstance(r, dict) and _nonempty(r.get("name"))}

    # ===== 架构门 =====
    arch_ok = True
    for role in roles:
        if not isinstance(role, dict):
            continue
        rid = role.get("id", "?")
        cu = role.get("code_units") or []
        existing = 0
        for c in cu:
            if not isinstance(c, str):
                continue
            ok, p = _file_exists(c, root)
            if ok:
                existing += 1
            else:
                issues.add("architecture", "critical", rid,
                           f"角色 {rid} 的 code_units 文件不存在：{c}",
                           str(p))
        if existing == 0 and cu:
            arch_ok = False
        elif not cu:
            issues.add("architecture", "critical", rid,
                       f"角色 {rid} 无 code_units（确认了角色却没代码）", "—")
            arch_ok = False
        # depends_on resolve
        for d in (role.get("depends_on") or []):
            if d not in id_set:
                issues.add("architecture", "critical", rid,
                           f"角色 {rid} depends_on 指向未定义角色 {d}", "—")
                arch_ok = False

    # ===== 日志门 =====
    log_re = STACK_LOG_RE.get(stack)
    all_units: list[str] = []
    for role in roles:
        if isinstance(role, dict):
            for c in (role.get("code_units") or []):
                if isinstance(c, str) and c not in all_units:
                    all_units.append(c)
    covered = 0
    zero_log: list[str] = []
    if log_re is None:
        issues.add("logging", "major", "—",
                   f"未知栈 {stack!r}，无法匹配日志关键字，日志门降级（登记缺口）", "—")
        log_ok = True  # 不因未知栈直接 no-go，但登记
    else:
        for u in all_units:
            ok, p = _file_exists(u, root)
            if not ok:
                continue  # 文件不存在已在架构门报过
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if log_re.search(txt):
                covered += 1
            else:
                zero_log.append(u)
                issues.add("logging", "minor", u,
                           f"代码单元无任何日志关键字（关键节点可能缺打点）：{u}", str(p))
        total = max(len(all_units), 1)
        log_ok = (covered / total) >= log_ratio
        if not log_ok:
            issues.add("logging", "critical", "—",
                       f"日志覆盖 {covered}/{len(all_units)}（{(covered/total)*100:.0f}%）"
                       f"低于阈值 {log_ratio*100:.0f}%：关键节点普遍缺日志", "—")

    # ===== 覆盖门 =====
    cov_ok = True
    for bp in bps:
        if not isinstance(bp, dict):
            continue
        step = bp.get("step", "?")
        for c in (bp.get("code_refs") or []):
            if not isinstance(c, str):
                continue
            ok, p = _file_exists(c, root)
            if not ok:
                issues.add("coverage", "critical", f"step:{step}",
                           f"流程 step:{step} 的 code_refs 文件不存在：{c}", str(p))
                cov_ok = False
        for pr in (bp.get("roles") or []):
            if pr not in id_set:
                issues.add("coverage", "critical", f"step:{step}",
                           f"流程 step:{step} roles 指向未定义角色 {pr}", "—")
                cov_ok = False
        if not _nonempty(bp.get("doc_ref")):
            issues.add("coverage", "major", f"step:{step}",
                       f"流程 step:{step} 缺 doc_ref（流程↔文档对不上）", "—")
            cov_ok = False
    # contract↔doc cross-check
    doc_roles = extract_doc_roles(doc_text)
    missing_in_doc = name_set - doc_roles
    if missing_in_doc:
        issues.add("coverage", "critical", "—",
                   f"契约角色未出现在文档角色职责表：{sorted(missing_in_doc)}", "—")
        cov_ok = False
    extra_in_doc = doc_roles - name_set
    if extra_in_doc:
        issues.add("coverage", "minor", "—",
                   f"文档角色表有契约未声明的角色（可能命名漂移）：{sorted(extra_in_doc)}", "—")
    meta, _body = split_frontmatter(doc_text)
    # frontmatter count consistency
    for fm_key, contract_val in (("roles_count", len(roles)), ("process_steps", len(bps))):
        fm_val = meta.get(fm_key)
        try:
            if fm_val is not None and int(fm_val) != contract_val:
                issues.add("coverage", "major", "—",
                           f"文档 frontmatter {fm_key}={fm_val} 与契约 {contract_val} 不一致", "—")
                cov_ok = False
        except ValueError:
            pass

    arch = "go" if arch_ok else "no-go"
    logg = "go" if log_ok else "no-go"
    cov = "go" if cov_ok else "no-go"
    verdict = "go" if (arch_ok and log_ok and cov_ok) else "no-go"

    return {
        "architecture": arch, "logging": logg, "coverage": cov,
        "verdict": verdict, "issues": issues.items,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Module E self-check gate for arch-first-code-gen")
    ap.add_argument("contract", type=Path, help="Path to design-contract.json")
    ap.add_argument("doc", type=Path, help="Path to <feature>-arch.md")
    ap.add_argument("--root", type=Path, default=Path.cwd(),
                    help="Repo root for file-existence checks (default CWD)")
    ap.add_argument("--logging-ratio", type=float, default=0.6,
                    help="Min fraction of code units with log keywords for logging gate (default 0.6)")
    args = ap.parse_args()

    for p, lbl in ((args.contract, "contract"), (args.doc, "doc")):
        if not p.exists():
            sys.stderr.write(f"{lbl} {p}: 文件不存在\n")
            return 2
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.contract}: JSON 解析失败：{exc}\n")
        return 2
    doc_text = args.doc.read_text(encoding="utf-8")

    if not isinstance(contract, dict):
        sys.stderr.write(f"{args.contract}: 顶层不是 JSON 对象（先跑 validate_contract.py）\n")
        return 2

    res = run(contract, doc_text, args.root, args.logging_ratio)

    print(f"=== validate_gate: {args.contract.name} + {args.doc.name} (root={args.root}) ===")
    print(f"架构门: {res['architecture']}    日志门: {res['logging']}    覆盖门: {res['coverage']}")
    print(f"重算 verdict: {res['verdict']}")
    declared = (contract.get("gate") or {}).get("verdict")
    print(f"契约声明 verdict: {declared}")
    if res["issues"]:
        print("\n问题清单：")
        sev_order = {"critical": 0, "major": 1, "minor": 2}
        for iss in sorted(res["issues"], key=lambda x: sev_order.get(x["severity"], 9)):
            print(f"  [{iss['severity']}] {iss['gate']}/{iss['role_or_step']}: {iss['problem']}"
                  + (f"  证据={iss['evidence']}" if iss["evidence"] not in ("—", "") else ""))
    else:
        print("\n问题清单：（无）")

    findings = []
    if res["verdict"] != "go":
        findings.append(f"重算 verdict={res['verdict']}（结构性证据需要复核，不自动等于不可交付）")
    if declared != res["verdict"]:
        findings.append(f"契约声明 verdict={declared!r} 与重算 {res['verdict']!r} 不一致（需要更新契约或在 notes 说明）")

    if findings:
        print("\n" + "\n".join("🟡 " + m for m in findings))
        print("\n结果：已输出辅助校验证据；请结合架构原则/代码设计原则复核。")
        return 0
    print("\n结果：辅助校验未发现结构性阻断证据（三道门全 go，且与契约声明一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
