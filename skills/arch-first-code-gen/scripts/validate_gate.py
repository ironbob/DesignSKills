#!/usr/bin/env python3
"""Module E advisory self-check runner for arch-first-code-gen.

This is an evidence aid, not a CI-style hard gate. It independently recomputes
the three structural checks from real files (not from the contract's self-claim),
so it catches stale or over-optimistic self-assessment. Final delivery judgment
still belongs to the architecture/code-design principle review.

Reads: design-contract.json (manifest) + <feature>-arch.md (render) + repo root
        (for file existence). File paths in the contract are repo-root-relative.

  G-ARCH  架构门: role files exist; dependencies resolve, are acyclic, and do
          not violate obvious stable-layer directions.
  G-LOG   日志门: per-stack log-keyword coverage. A code unit with zero log
          calls ⇒ minor; logging = no-go when zero-log ratio > (1-ratio)
          (default covered ratio < 0.6). Honest structural proxy (PRD §6).
  G-COV   覆盖门: each business_process step's code_refs file and named symbol
          exist, roles are valid, doc_ref occurs in the document; every contract
          role name appears in the doc 角色职责清单 table; frontmatter
          roles_count/process_steps/verdict consistent with the contract.
  G-VER   验证门: executed commands/checks carry evidence and have no failures.

Recomputed verdict = go iff all four checks go. By default a recomputed no-go is
advisory; ``--strict`` exits 1 for no-go or contract drift and is required for
delivery. Semantic items (is a responsibility *truly* single?) remain outside
machine checking — register them in gate.notes / 已知缺口, never fake-verified.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tokenize
from pathlib import Path
from typing import Any

from run_verification import fingerprint_inputs

STACK_LOG_RE = {
    "JVM": re.compile(r"\b(?:log|logger|LOGGER|log_)\s*\."),
    "C++": re.compile(r"spdlog::"),
    "FastAPI+Vue": re.compile(r"\b(?:logger|log|logging)\s*(?:\.|::)"),
    "Swift/iOS": re.compile(r"(?:\b(?:logger|log|Logger)\s*\.|\bos_log\s*\()"),
}

SWIFT_LOGGING_LAYERS = {
    "view_model", "application", "service", "repository", "infrastructure",
    "coordinator", "composition", "store",
}

FORBIDDEN_TARGET_LAYERS = {
    "domain": {"controller", "router", "view", "view_model", "service", "application", "infrastructure"},
    "repository": {"controller", "router", "view", "view_model"},
    "service": {"controller", "router", "view"},
    "application": {"controller", "router", "view"},
    "view_model": {"view"},
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
    resolved_root = root.resolve()
    p = (resolved_root / path_part).resolve() if not Path(path_part).is_absolute() else Path(path_part).resolve()
    try:
        p.relative_to(resolved_root)
        return p.exists(), p
    except ValueError:
        return False, p
    except OSError:
        return False, p


def _ref_exists(rel: str, root: Path) -> tuple[bool, bool, Path, str | None]:
    """Return file existence and a text-level symbol existence approximation."""
    path_part, sep, symbol = rel.partition(":")
    ok, path = _file_exists(path_part, root)
    if not ok or not sep or not symbol:
        return ok, bool(ok and not symbol), path, symbol or None
    try:
        source = _source_without_comments_and_strings(path)
    except OSError:
        return ok, False, path, symbol
    token = symbol.rsplit(".", 1)[-1].strip()
    symbol_ok = bool(token and re.search(rf"\b{re.escape(token)}\b", source))
    return ok, symbol_ok, path, symbol


def _dependency_cycle(graph: dict[str, list[str]]) -> list[str] | None:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = stack.index(node)
            return stack[start:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for target in graph.get(node, []):
            cycle = visit(target)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in graph:
        cycle = visit(node)
        if cycle:
            return cycle
    return None


def _source_without_comments_and_strings(path: Path) -> str:
    """Return a lightweight lexical view suitable for role-name dependency checks."""
    source = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".py":
        try:
            tokens = tokenize.generate_tokens(io.StringIO(source).readline)
            return " ".join(
                token.string for token in tokens
                if token.type not in {tokenize.COMMENT, tokenize.STRING, tokenize.ENCODING}
            )
        except (tokenize.TokenError, IndentationError):
            return source

    output: list[str] = []
    i = 0
    state = "code"
    quote = ""
    while i < len(source):
        char = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if char == "/" and nxt == "/":
                state = "line_comment"
                output.extend("  ")
                i += 2
                continue
            if char == "/" and nxt == "*":
                state = "block_comment"
                output.extend("  ")
                i += 2
                continue
            if char in {'"', "'"}:
                state = "string"
                quote = char
                output.append(" ")
                i += 1
                continue
            output.append(char)
            i += 1
            continue
        if state == "line_comment":
            if char == "\n":
                state = "code"
                output.append("\n")
            else:
                output.append(" ")
            i += 1
            continue
        if state == "block_comment":
            if char == "*" and nxt == "/":
                state = "code"
                output.extend("  ")
                i += 2
            else:
                output.append("\n" if char == "\n" else " ")
                i += 1
            continue
        if state == "string":
            if char == "\\":
                output.extend("  ")
                i += 2
            elif char == quote:
                state = "code"
                output.append(" ")
                i += 1
            else:
                output.append("\n" if char == "\n" else " ")
                i += 1
    return "".join(output)


def _source_reference_exception_ids(role: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in role.get("source_reference_exceptions") or []:
        if isinstance(item, str):
            ids.add(item)
        elif isinstance(item, dict) and isinstance(item.get("role"), str):
            ids.add(item["role"])
    return ids


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


def run(contract: dict, doc_text: str, root: Path, log_ratio: float,
        source_dependency_check: bool = False) -> dict:
    issues = Issues()
    stack = contract.get("stack", "")
    roles = contract.get("roles") or []
    bps = contract.get("business_process") or []
    id_set = {r.get("id") for r in roles if isinstance(r, dict)}
    role_by_id = {r.get("id"): r for r in roles if isinstance(r, dict)}
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
                continue
            target = role_by_id.get(d) or {}
            forbidden = FORBIDDEN_TARGET_LAYERS.get(role.get("layer"), set())
            if target.get("layer") in forbidden:
                issues.add("architecture", "critical", rid,
                           f"明显反向/跨层依赖：{rid}({role.get('layer')}) → {d}({target.get('layer')})", "depends_on")
                arch_ok = False
    graph = {
        str(role.get("id")): [str(d) for d in (role.get("depends_on") or []) if d in id_set]
        for role in roles if isinstance(role, dict) and role.get("id") in id_set
    }
    cycle = _dependency_cycle(graph)
    if cycle:
        issues.add("architecture", "critical", cycle[0],
                   f"依赖图存在环：{' → '.join(cycle)}", "depends_on")
        arch_ok = False

    if source_dependency_check:
        for role in roles:
            if not isinstance(role, dict):
                continue
            rid = role.get("id", "?")
            declared = set(role.get("depends_on") or [])
            exceptions = _source_reference_exception_ids(role)
            role_units = set(role.get("code_units") or [])
            combined_source = ""
            for unit in role_units:
                ok, path = _file_exists(unit, root)
                if ok and path.is_file():
                    try:
                        combined_source += "\n" + _source_without_comments_and_strings(path)
                    except OSError:
                        continue
            for target in roles:
                if not isinstance(target, dict) or target.get("id") == rid:
                    continue
                target_id = target.get("id")
                target_name = target.get("name")
                if not isinstance(target_id, str) or not _nonempty(target_name):
                    continue
                if role_units.intersection(set(target.get("code_units") or [])):
                    continue
                if re.search(rf"\b{re.escape(target_name)}\b", combined_source):
                    if target_id not in declared and target_id not in exceptions:
                        issues.add(
                            "architecture", "critical", str(rid),
                            f"源码引用 {target_name}({target_id})，但 depends_on 未声明且无 source_reference_exceptions",
                            ", ".join(sorted(role_units)),
                        )
                        arch_ok = False

    # ===== 日志门 =====
    log_re = STACK_LOG_RE.get(stack)
    all_units: list[str] = []
    for role in roles:
        if isinstance(role, dict):
            if role.get("role_kind") == "domain" or role.get("layer") in {"view", "mapper", "util"}:
                continue
            if stack == "Swift/iOS" and role.get("layer") not in SWIFT_LOGGING_LAYERS:
                continue
            for c in (role.get("code_units") or []):
                if isinstance(c, str) and c not in all_units:
                    all_units.append(c)
    covered = 0
    zero_log: list[str] = []
    if log_re is None:
        issues.add("logging", "major", "—",
                   f"未知栈 {stack!r}，无法匹配日志关键字，日志门降级（登记缺口）", "—")
        log_ok = True  # 不因未知栈直接 no-go，但登记
    elif not all_units:
        log_ok = True  # 例如 Swift/iOS 纯展示 feature，没有应打日志的流程角色
    else:
        for u in all_units:
            ok, p = _file_exists(u, root)
            if not ok:
                continue  # 文件不存在已在架构门报过
            try:
                txt = _source_without_comments_and_strings(p)
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
            file_ok, symbol_ok, p, symbol = _ref_exists(c, root)
            if not file_ok:
                issues.add("coverage", "critical", f"step:{step}",
                           f"流程 step:{step} 的 code_refs 文件不存在：{c}", str(p))
                cov_ok = False
            elif symbol and not symbol_ok:
                issues.add("coverage", "critical", f"step:{step}",
                           f"流程 step:{step} 的 code_refs 符号不存在：{symbol}", str(p))
                cov_ok = False
        for pr in (bp.get("roles") or []):
            if pr not in id_set:
                issues.add("coverage", "critical", f"step:{step}",
                           f"流程 step:{step} roles 指向未定义角色 {pr}", "—")
                cov_ok = False
        doc_ref = bp.get("doc_ref")
        if not _nonempty(doc_ref):
            issues.add("coverage", "major", f"step:{step}",
                       f"流程 step:{step} 缺 doc_ref（流程↔文档对不上）", "—")
            cov_ok = False
        elif doc_ref not in doc_text:
            issues.add("coverage", "major", f"step:{step}",
                       f"流程 step:{step} 的 doc_ref 未在文档出现：{doc_ref}", "arch.md")
            cov_ok = False
    for trace in (contract.get("traceability") or []):
        if not isinstance(trace, dict):
            continue
        trace_id = str(trace.get("id", "trace"))
        for code_ref in (trace.get("code_refs") or []):
            if not isinstance(code_ref, str):
                continue
            file_ok, symbol_ok, path, symbol = _ref_exists(code_ref, root)
            if not file_ok:
                issues.add("coverage", "critical", trace_id,
                           f"追踪链 code_refs 文件不存在：{code_ref}", str(path))
                cov_ok = False
            elif symbol and not symbol_ok:
                issues.add("coverage", "critical", trace_id,
                           f"追踪链 code_refs 符号不存在：{symbol}", str(path))
                cov_ok = False
    for interface in (contract.get("interfaces") or []):
        if not isinstance(interface, dict):
            continue
        iid = interface.get("id", "?")
        if interface.get("provider") not in id_set or any(c not in id_set for c in (interface.get("consumers") or [])):
            issues.add("coverage", "critical", iid, "接口 provider/consumers 指向未定义角色", "interfaces")
            cov_ok = False
        name = interface.get("name")
        if _nonempty(name) and name not in doc_text:
            issues.add("coverage", "major", iid, f"接口未在架构文档出现：{name}", "arch.md")
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
    declared_profile = (contract.get("design_decision") or {}).get("profile")
    if meta.get("design_profile") != declared_profile:
        issues.add("coverage", "major", "—",
                   f"文档 design_profile={meta.get('design_profile')!r} 与契约 {declared_profile!r} 不一致", "frontmatter")
        cov_ok = False
    declared_verdict = (contract.get("gate") or {}).get("verdict")
    if meta.get("verdict") != declared_verdict:
        issues.add("coverage", "major", "—",
                   f"文档 verdict={meta.get('verdict')!r} 与契约 {declared_verdict!r} 不一致", "frontmatter")
        cov_ok = False

    # ===== 验证门 =====
    ver_ok = True
    verification = contract.get("verification") or {}
    commands = verification.get("commands") or []
    checks = verification.get("checks") or []
    if not commands or not checks:
        issues.add("verification", "critical", "—", "缺实际验证命令或关键检查映射", "verification")
        ver_ok = False
    for i, item in enumerate(commands):
        if not isinstance(item, dict):
            ver_ok = False
            continue
        is_v2_command = isinstance(item.get("argv"), list)
        command_label = item.get("id") or item.get("command")
        if item.get("status") == "failed":
            issues.add("verification", "critical", f"command:{i + 1}",
                       f"验证命令失败：{command_label}", str(item.get("execution") or item.get("evidence", "—")))
            ver_ok = False
        elif item.get("status") in {"pending", None}:
            issues.add("verification", "critical", f"command:{i + 1}",
                       f"验证命令尚未执行：{command_label}", "run_verification.py")
            ver_ok = False
        elif item.get("status") == "skipped":
            issues.add("verification", "minor", f"command:{i + 1}",
                       f"验证命令被跳过：{command_label}", str(item.get("execution") or item.get("evidence", "—")))
            if item.get("required", False):
                ver_ok = False
        if is_v2_command and not isinstance(item.get("execution"), dict):
            issues.add("verification", "major", f"command:{i + 1}", "验证命令缺机器 execution 证据", "verification")
            ver_ok = False
        elif is_v2_command:
            try:
                current_inputs_hash = fingerprint_inputs(root, item.get("inputs") or [])
            except (OSError, ValueError) as exc:
                issues.add("verification", "critical", f"command:{i + 1}",
                           f"验证输入不可读取：{exc}", "verification.inputs")
                ver_ok = False
            else:
                if item["execution"].get("inputs_sha256") != current_inputs_hash:
                    issues.add("verification", "critical", f"command:{i + 1}",
                               f"验证输入在执行后已漂移：{command_label}", "重新运行 run_verification.py")
                    ver_ok = False
        elif not is_v2_command and not _nonempty(item.get("evidence")):
            issues.add("verification", "major", f"command:{i + 1}", "验证命令缺 evidence", "verification")
            ver_ok = False
    for i, item in enumerate(checks):
        if not isinstance(item, dict):
            ver_ok = False
            continue
        if item.get("status") == "failed":
            issues.add("verification", "critical", f"check:{i + 1}",
                       f"关键检查失败：{item.get('target')}", str(item.get("evidence", "—")))
            ver_ok = False
        elif item.get("status") in {"pending", None}:
            issues.add("verification", "critical", f"check:{i + 1}",
                       f"关键检查尚未执行：{item.get('target')}", str(item.get("evidence", "—")))
            ver_ok = False
        elif item.get("status") == "skipped":
            issues.add("verification", "minor", f"check:{i + 1}",
                       f"关键检查被跳过：{item.get('target')}", str(item.get("evidence", "—")))
        if not _nonempty(item.get("evidence")):
            issues.add("verification", "major", f"check:{i + 1}", "关键检查缺 evidence", "verification")
            ver_ok = False
    for item in (verification.get("unverified") or []):
        if isinstance(item, dict):
            issues.add("verification", "minor", "unverified",
                       f"仍有未验证项：{item.get('item')}", str(item.get("impact", "—")))
    if contract.get("contract_version") == 2:
        if not contract.get("traceability"):
            issues.add("verification", "critical", "traceability", "缺验收到代码/测试/命令的追踪链", "traceability")
            ver_ok = False
        review = (contract.get("construction_review") or {}).get("items") or []
        not_ready = [
            item.get("principle") for item in review
            if isinstance(item, dict) and item.get("status") in {"failed", "not_reviewed", None}
        ]
        if not_ready:
            issues.add("verification", "critical", "construction_review",
                       f"Code Complete 构造复核未就绪：{not_ready}", "construction_review")
            ver_ok = False

    arch = "go" if arch_ok else "no-go"
    logg = "go" if log_ok else "no-go"
    cov = "go" if cov_ok else "no-go"
    ver = "go" if ver_ok else "no-go"
    verdict = "go" if (arch_ok and log_ok and cov_ok and ver_ok) else "no-go"

    return {
        "architecture": arch, "logging": logg, "coverage": cov, "verification": ver,
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
    ap.add_argument("--source-dependency-check", action="store_true",
                    help="Compare role-name references in source files with declared depends_on")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 when recomputed verdict is no-go or differs from the contract")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--summary", action="store_true", help="Compact output (default)")
    mode.add_argument("--verbose", action="store_true", help="Print full gate details")
    ap.add_argument("--json-output", type=Path, help="Write a machine-readable result")
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

    res = run(contract, doc_text, args.root, args.logging_ratio, args.source_dependency_check)
    declared = (contract.get("gate") or {}).get("verdict")
    drift = declared != res["verdict"]
    if args.json_output:
        payload = dict(res)
        payload["declared_verdict"] = declared
        payload["drift"] = drift
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.verbose:
        print(f"=== validate_gate: {args.contract.name} + {args.doc.name} (root={args.root}) ===")
        print(f"架构门: {res['architecture']}    日志门: {res['logging']}    覆盖门: {res['coverage']}    验证门: {res['verification']}")
        print(f"重算 verdict: {res['verdict']}")
        print(f"契约声明 verdict: {declared}")
        if res["issues"]:
            print("\n问题清单：")
            sev_order = {"critical": 0, "major": 1, "minor": 2}
            for iss in sorted(res["issues"], key=lambda x: sev_order.get(x["severity"], 9)):
                print(f"  [{iss['severity']}] {iss['gate']}/{iss['role_or_step']}: {iss['problem']}"
                      + (f"  证据={iss['evidence']}" if iss["evidence"] not in ("—", "") else ""))
        else:
            print("\n问题清单：（无）")
    else:
        print(
            f"gates: {'PASS' if res['verdict'] == 'go' and not drift else 'FAIL'} "
            f"(architecture={res['architecture']}, logging={res['logging']}, "
            f"coverage={res['coverage']}, verification={res['verification']}, issues={len(res['issues'])})"
        )
        if res["verdict"] != "go" or drift:
            for iss in res["issues"]:
                print(f"[{iss['severity']}] {iss['gate']}/{iss['role_or_step']}: {iss['problem']}")

    findings = []
    if res["verdict"] != "go":
        findings.append(f"重算 verdict={res['verdict']}（结构性证据需要复核，不自动等于不可交付）")
    if drift:
        findings.append(f"契约声明 verdict={declared!r} 与重算 {res['verdict']!r} 不一致（需要更新契约或在 notes 说明）")

    if findings:
        if args.verbose:
            print("\n" + "\n".join("🟡 " + m for m in findings))
            print("\n结果：已输出辅助校验证据；请结合架构原则/代码设计原则复核。")
        return 1 if args.strict else 0
    if args.verbose:
        print("\n结果：辅助校验未发现结构性阻断证据（四道门全 go，且与契约声明一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
