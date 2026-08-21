#!/usr/bin/env python3
"""Create a compact, deterministic fact index for architecture diagnosis.

The scanner does not decide whether a smell exists. It collects source files,
package/namespace declarations, import/include edges, simple hotspot signals,
and optional git co-change history so the evaluating agent can read less code.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

from scan_cpp_semantics import scan_cpp_semantics

SOURCE_SUFFIXES = {".java", ".kt", ".h", ".hpp", ".hh", ".cc", ".cpp", ".cxx"}
JVM_SUFFIXES = {".java", ".kt"}
CPP_SUFFIXES = SOURCE_SUFFIXES - JVM_SUFFIXES
EXCLUDED_PARTS = {
    ".git", ".gradle", ".idea", "build", "dist", "generated", "node_modules",
    "out", "target", "test", "tests", "testdata", "fixtures",
}
PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)", re.M)
IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)", re.M)
INCLUDE_RE = re.compile(r'^\s*#\s*include\s*[<"]([^>"]+)[>"]', re.M)
NAMESPACE_RE = re.compile(r"\bnamespace\s+([A-Za-z_]\w*)")
PUBLIC_RE = re.compile(r"\bpublic\b|^\s*public\s*:", re.M)
TYPE_REF_RE = re.compile(r"\b[A-Z][A-Za-z0-9_]*\b")


def relative_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path.resolve())


def is_excluded(path: Path, include_tests: bool) -> bool:
    blocked = EXCLUDED_PARTS - ({"test", "tests", "testdata", "fixtures"} if include_tests else set())
    return any(part.lower() in blocked for part in path.parts)


def source_files(paths: Iterable[Path], include_tests: bool) -> list[Path]:
    found: set[Path] = set()
    for raw in paths:
        path = raw.resolve()
        candidates = [path] if path.is_file() else path.rglob("*") if path.is_dir() else []
        for item in candidates:
            if item.is_file() and item.suffix.lower() in SOURCE_SUFFIXES and not is_excluded(item, include_tests):
                found.add(item)
    return sorted(found)


def language_for(files: list[Path]) -> str:
    jvm = sum(path.suffix.lower() in JVM_SUFFIXES for path in files)
    cpp = sum(path.suffix.lower() in CPP_SUFFIXES for path in files)
    if jvm == cpp:
        jvm_size = sum(path.stat().st_size for path in files if path.suffix.lower() in JVM_SUFFIXES)
        cpp_size = sum(path.stat().st_size for path in files if path.suffix.lower() in CPP_SUFFIXES)
        if jvm_size == cpp_size:
            raise ValueError("无法识别主体语言；请用 --language JVM 或 --language C++ 指定")
        return "JVM" if jvm_size > cpp_size else "C++"
    return "JVM" if jvm > cpp else "C++"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def inspect_file(path: Path, root: Path) -> dict:
    text = read_text(path)
    suffix = path.suffix.lower()
    dependencies: list[dict] = []
    if suffix in JVM_SUFFIXES:
        package_match = PACKAGE_RE.search(text)
        package = package_match.group(1) if package_match else None
        namespaces: list[str] = []
        dep_re = IMPORT_RE
        kind = "import"
    else:
        package = None
        namespaces = sorted(set(NAMESPACE_RE.findall(text)))
        dep_re = INCLUDE_RE
        kind = "include"
    for match in dep_re.finditer(text):
        line = text.count("\n", 0, match.start()) + 1
        dependencies.append({"kind": kind, "target": match.group(1), "line": line})
    return {
        "file": relative_to_root(path, root),
        "lines": text.count("\n") + (0 if not text or text.endswith("\n") else 1),
        "package": package,
        "namespaces": namespaces,
        "dependency_count": len(dependencies),
        "public_signal_count": len(PUBLIC_RE.findall(text)),
        "dependencies": dependencies,
    }


def add_internal_type_edges(facts: list[dict], files: list[Path]) -> None:
    """Resolve simple JVM/C++ type references to files inside the confirmed scope."""
    symbols: dict[str, list[str]] = {}
    for path, fact in zip(files, facts):
        symbols.setdefault(path.stem, []).append(fact["file"])
    for path, fact in zip(files, facts):
        text = read_text(path)
        existing = {(item["target"], item["line"]) for item in fact["dependencies"]}
        for match in TYPE_REF_RE.finditer(text):
            symbol = match.group(0)
            targets = symbols.get(symbol, [])
            if len(targets) != 1 or targets[0] == fact["file"]:
                continue
            line = text.count("\n", 0, match.start()) + 1
            key = (symbol, line)
            if key in existing:
                continue
            fact["dependencies"].append({
                "kind": "internal-type-reference",
                "target": symbol,
                "resolved_file": targets[0],
                "line": line,
            })
            existing.add(key)
        fact["dependencies"].sort(key=lambda item: (item["line"], item["target"]))
        fact["dependency_count"] = len(fact["dependencies"])


def dependency_cycles(edges: list[dict]) -> list[list[str]]:
    """Return deterministic SCC cycle candidates from resolved internal file edges."""
    graph: dict[str, set[str]] = {}
    for edge in edges:
        source = str(edge.get("from", ""))
        target = edge.get("resolved_file")
        if source and isinstance(target, str) and target and source != target:
            graph.setdefault(source, set()).add(target)
            graph.setdefault(target, set())
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    components: list[list[str]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph.get(node, set())):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])
        if lowlinks[node] == indices[node]:
            component = []
            while stack:
                current = stack.pop()
                on_stack.remove(current)
                component.append(current)
                if current == node:
                    break
            if len(component) > 1:
                components.append(sorted(component))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(components)


def git_cochanges(root: Path, covered: set[str], commits: int, limit: int) -> dict:
    if commits <= 0:
        return {"available": False, "commits_sampled": 0, "cochange_hotspots": []}
    try:
        proc = subprocess.run(
            ["git", "log", f"-n{commits}", "--name-only", "--format=__ARCH_COMMIT__", "--"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"available": False, "commits_sampled": 0, "cochange_hotspots": []}
    if proc.returncode != 0:
        return {"available": False, "commits_sampled": 0, "cochange_hotspots": []}

    groups: list[set[str]] = []
    current: set[str] = set()
    for raw in proc.stdout.splitlines():
        line = raw.strip()
        if line == "__ARCH_COMMIT__":
            if current:
                groups.append(current)
            current = set()
        elif line in covered:
            current.add(line)
    if current:
        groups.append(current)

    pairs: Counter[tuple[str, str]] = Counter()
    for group in groups:
        for pair in itertools.combinations(sorted(group), 2):
            pairs[pair] += 1
    hotspots = [
        {"files": list(pair), "commit_count": count}
        for pair, count in pairs.most_common(limit)
        if count >= 2
    ]
    return {"available": True, "commits_sampled": len(groups), "cochange_hotspots": hotspots}


def build_scan(args: argparse.Namespace) -> dict:
    root = args.root.resolve()
    requested = [(root / raw).resolve() if not raw.is_absolute() else raw.resolve() for raw in args.paths]
    files = source_files(requested, args.include_tests)
    if not files:
        raise ValueError("指定范围内未找到 JVM/C++ 源文件")
    language = args.language or language_for(files)
    index_workers = args.scan_jobs if len(files) >= 32 else 1
    with ThreadPoolExecutor(max_workers=index_workers) as executor:
        facts = list(executor.map(lambda path: inspect_file(path, root), files))
    add_internal_type_edges(facts, files)
    covered = {fact["file"] for fact in facts}
    cpp_semantics = None
    with ThreadPoolExecutor(max_workers=2) as background:
        git_future = background.submit(
            git_cochanges, root, covered, args.git_history, args.max_cochanges
        )
        cpp_future = None
        if language == "C++" and args.cpp_mode != "text":
            cpp_future = background.submit(
                scan_cpp_semantics,
                root,
                files,
                args.compile_commands,
                args.cpp_ast_filter,
                args.cpp_timeout,
                args.cpp_jobs,
            )
        elif language == "C++":
            cpp_semantics = {"backend": "text-search", "reason": "disabled by --cpp-mode text"}
        hotspots = sorted(
            (
                {
                    "file": fact["file"],
                    "lines": fact["lines"],
                    "dependency_count": fact["dependency_count"],
                    "public_signal_count": fact["public_signal_count"],
                }
                for fact in facts
            ),
            key=lambda item: (item["dependency_count"] * 4 + item["public_signal_count"] * 2 + item["lines"], item["file"]),
            reverse=True,
        )[: args.max_hotspots]
        dependency_edges = [
            {"from": fact["file"], **dependency}
            for fact in facts
            for dependency in fact["dependencies"]
        ]
        if cpp_future is not None:
            cpp_semantics = cpp_future.result()
        git = git_future.result()
    if args.cpp_mode == "clang" and language == "C++" and (cpp_semantics or {}).get("backend") != "clang-ast":
        raise ValueError(f"C++ clang AST 模式不可用：{(cpp_semantics or {}).get('reason', 'unknown error')}")
    packages = sorted({fact["package"] for fact in facts if fact["package"]})
    namespaces = sorted({name for fact in facts for name in fact["namespaces"]})
    return {
        "version": 1,
        "root": str(root),
        "input_paths": [relative_to_root(path, root) for path in requested],
        "language": language,
        "cpp_limitation_noted": language == "C++",
        "semantic_backend": cpp_semantics.get("backend") if cpp_semantics else "text-search",
        "covered_files": sorted(covered),
        "files": facts,
        "structure": {"packages": packages, "namespaces": namespaces},
        "hotspots": hotspots,
        "dependency_edges": dependency_edges,
        "dependency_edge_count": len(dependency_edges),
        "dependency_edges_truncated": False,
        "cycle_candidates": dependency_cycles(dependency_edges),
        "cpp_semantics": cpp_semantics,
        "git": git,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan JVM/C++ architecture facts without judging smells")
    parser.add_argument("paths", nargs="+", type=Path, help="Module paths, relative to --root unless absolute")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--output", type=Path, help="Write JSON here; default stdout")
    parser.add_argument("--language", choices=("JVM", "C++"), help="Override mixed-language primary language")
    parser.add_argument("--cpp-mode", choices=("auto", "clang", "text"), default="auto",
                        help="C++ semantic backend; auto prefers compile_commands + clang AST")
    parser.add_argument("--compile-commands", type=Path, help="compile_commands.json path relative to --root")
    parser.add_argument("--cpp-ast-filter", help="Optional explicit clang declaration filter; omit for full project coverage")
    parser.add_argument("--cpp-timeout", type=int, default=30, help="Per translation-unit clang timeout in seconds")
    default_jobs = min(os.cpu_count() or 1, 4)
    parser.add_argument("--scan-jobs", type=int, default=default_jobs,
                        help="Bounded workers for deterministic source indexing")
    parser.add_argument("--cpp-jobs", type=int, default=default_jobs,
                        help="Bounded workers for independent C++ translation units")
    parser.add_argument("--include-tests", action="store_true", help="Include test/fixture paths")
    parser.add_argument("--git-history", type=int, default=100, help="Recent commits sampled for co-change facts; 0 disables")
    parser.add_argument("--max-hotspots", type=int, default=20)
    parser.add_argument("--max-edges", type=int, default=500,
                        help="Deprecated compatibility option; v2 never truncates the on-disk fact index")
    parser.add_argument("--max-cochanges", type=int, default=30)
    args = parser.parse_args()
    if args.scan_jobs < 1 or args.cpp_jobs < 1:
        parser.error("--scan-jobs and --cpp-jobs must be positive")
    try:
        scan = build_scan(args)
    except ValueError as exc:
        sys.stderr.write(f"scan_architecture: {exc}\n")
        return 2
    payload = json.dumps(scan, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
