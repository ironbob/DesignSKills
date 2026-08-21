#!/usr/bin/env python3
"""Extract compact C++ semantic facts with compile_commands.json and clang AST."""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

CPP_SOURCE_SUFFIXES = {".cc", ".cpp", ".cxx"}
TYPE_NODE_KINDS = {
    "FieldDecl": "field-type",
    "ParmVarDecl": "parameter-type",
    "VarDecl": "variable-type",
    "MemberExpr": "member-reference",
    "CXXConstructExpr": "construction",
    "CXXTemporaryObjectExpr": "construction",
    "CXXNewExpr": "allocation",
}


def rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def find_compile_database(root: Path, explicit: Path | None) -> Path | None:
    if explicit:
        candidate = explicit if explicit.is_absolute() else root / explicit
        return candidate.resolve() if candidate.is_file() else None
    for candidate in (
        root / "compile_commands.json",
        root / "build" / "compile_commands.json",
        root / "out" / "compile_commands.json",
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None


def load_entries(database: Path) -> list[dict[str, Any]]:
    data = json.loads(database.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("compile_commands.json 顶层须为数组")
    return [entry for entry in data if isinstance(entry, dict)]


def entry_directory(entry: dict[str, Any], database: Path) -> Path:
    value = Path(str(entry.get("directory") or database.parent))
    return value.resolve() if value.is_absolute() else (database.parent / value).resolve()


def entry_file(entry: dict[str, Any], database: Path) -> Path:
    directory = entry_directory(entry, database)
    value = Path(str(entry.get("file", "")))
    return value.resolve() if value.is_absolute() else (directory / value).resolve()


def entry_args(entry: dict[str, Any]) -> list[str]:
    args = entry.get("arguments")
    if isinstance(args, list) and all(isinstance(item, str) for item in args):
        return list(args)
    command = entry.get("command")
    if isinstance(command, str):
        return shlex.split(command)
    return []


def sanitize_args(args: list[str], source: Path, directory: Path, clang: str) -> list[str]:
    if args:
        args = args[1:]
    out: list[str] = [clang]
    skip_next = False
    value_flags = {
        "-o", "-MF", "-MT", "-MQ", "-MJ", "--serialize-diagnostics",
        "-Xclang", "-load", "-plugin", "-add-plugin", "--config", "-B",
    }
    ignored = {"-c", "-MMD", "-MD", "-MP"}
    for index, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in value_flags:
            skip_next = True
            continue
        if arg in ignored:
            continue
        if arg.startswith(("@", "-fplugin=", "-plugin-arg-", "--config=")):
            continue
        arg_path = Path(arg)
        resolved = arg_path.resolve() if arg_path.is_absolute() else (directory / arg_path).resolve()
        if resolved == source:
            continue
        out.append(arg)
    return out


def json_stream(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    cursor = 0
    values: list[dict[str, Any]] = []
    while cursor < len(text):
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text):
            break
        value, cursor = decoder.raw_decode(text, cursor)
        if isinstance(value, dict):
            values.append(value)
    return values


def node_file(node: dict[str, Any], inherited: Path | None, directory: Path) -> Path | None:
    loc = node.get("loc") if isinstance(node.get("loc"), dict) else {}
    begin = (node.get("range") or {}).get("begin") if isinstance(node.get("range"), dict) else {}
    raw = loc.get("file") or (begin.get("file") if isinstance(begin, dict) else None)
    if raw:
        value = Path(str(raw))
        return value.resolve() if value.is_absolute() else (directory / value).resolve()
    return inherited


def node_line(node: dict[str, Any], file: Path | None) -> int | None:
    loc = node.get("loc") if isinstance(node.get("loc"), dict) else {}
    begin = (node.get("range") or {}).get("begin") if isinstance(node.get("range"), dict) else {}
    line = loc.get("line") or (begin.get("line") if isinstance(begin, dict) else None)
    if isinstance(line, int):
        return line
    offset = loc.get("offset") or (begin.get("offset") if isinstance(begin, dict) else None)
    if isinstance(offset, int) and file and file.is_file():
        data = file.read_bytes()
        return data[:offset].count(b"\n") + 1
    return None


def collect_records(
    node: dict[str, Any], directory: Path, covered: set[Path],
    inherited_file: Path | None = None, namespaces: tuple[str, ...] = (),
    records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    records = records if records is not None else []
    file = node_file(node, inherited_file, directory)
    current_namespaces = namespaces
    if node.get("kind") == "NamespaceDecl" and node.get("name"):
        current_namespaces = (*namespaces, str(node["name"]))
    if (
        node.get("kind") == "CXXRecordDecl"
        and node.get("name")
        and node.get("completeDefinition") is True
        and file in covered
    ):
        name = str(node["name"])
        records.append({
            "id": str(node.get("id", "")),
            "name": name,
            "qualified_name": "::".join((*current_namespaces, name)),
            "file": file,
            "line": node_line(node, file),
        })
    for child in node.get("inner", []):
        if isinstance(child, dict):
            collect_records(child, directory, covered, file, current_namespaces, records)
    return records


def collect_edges(
    node: dict[str, Any], directory: Path, covered: set[Path], records: list[dict[str, Any]],
    inherited_file: Path | None = None, current_record: dict[str, Any] | None = None,
    edges: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    edges = edges if edges is not None else []
    file = node_file(node, inherited_file, directory)
    record_by_id = {record["id"]: record for record in records}
    if node.get("kind") == "CXXRecordDecl" and str(node.get("id", "")) in record_by_id:
        current_record = record_by_id[str(node["id"])]
    kind = TYPE_NODE_KINDS.get(str(node.get("kind")))
    node_type = node.get("type") if isinstance(node.get("type"), dict) else {}
    qual_type = str(node_type.get("qualType", ""))
    if kind and current_record and file in covered and qual_type:
        for target in records:
            if target["id"] == current_record["id"]:
                continue
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(target['name'])}(?![A-Za-z0-9_])", qual_type):
                edges.append({
                    "from_type": current_record["qualified_name"],
                    "to_type": target["qualified_name"],
                    "file": file,
                    "line": node_line(node, file),
                    "kind": kind,
                    "qual_type": qual_type,
                })
    for child in node.get("inner", []):
        if isinstance(child, dict):
            collect_edges(child, directory, covered, records, file, current_record, edges)
    return edges


def dedupe(items: Iterable[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    result = []
    for item in items:
        signature = tuple(item.get(key) for key in keys)
        if signature in seen:
            continue
        seen.add(signature)
        result.append(item)
    return result


def scan_cpp_semantics(
    root: Path, files: list[Path], compile_commands: Path | None = None,
    ast_filter: str | None = None, timeout: int = 30,
) -> dict[str, Any]:
    root = root.resolve()
    covered = {path.resolve() for path in files}
    database = find_compile_database(root, compile_commands)
    clang = shutil.which("clang++")
    if not database:
        return {"backend": "text-search", "reason": "compile_commands.json not found"}
    if not clang:
        return {"backend": "text-search", "reason": "clang++ not found", "compile_commands": rel(database, root)}
    try:
        entries = load_entries(database)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return {"backend": "text-search", "reason": f"invalid compile database: {exc}", "compile_commands": rel(database, root)}

    source_entries = [
        entry for entry in entries
        if entry_file(entry, database) in covered and entry_file(entry, database).suffix.lower() in CPP_SOURCE_SUFFIXES
    ]
    if not source_entries:
        return {
            "backend": "text-search",
            "reason": "no covered C++ translation unit in compile database",
            "compile_commands": rel(database, root),
        }

    if not ast_filter:
        namespace_roots = []
        namespace_re = re.compile(r"\bnamespace\s+([A-Za-z_]\w*)")
        for path in covered:
            if path.is_file():
                namespace_roots.extend(namespace_re.findall(path.read_text(encoding="utf-8", errors="replace")))
        ast_filter = namespace_roots[0] if namespace_roots else None

    all_records: list[dict[str, Any]] = []
    all_edges: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    parsed_units = 0
    for entry in source_entries:
        directory = entry_directory(entry, database)
        source = entry_file(entry, database)
        command = sanitize_args(entry_args(entry), source, directory, clang)
        command.extend(["-fsyntax-only", "-Xclang", "-ast-dump=json"])
        if ast_filter:
            command.extend(["-Xclang", f"-ast-dump-filter={ast_filter}"])
        command.append(str(source))
        try:
            proc = subprocess.run(
                command, cwd=directory, capture_output=True, text=True,
                check=False, timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            failures.append({"file": rel(source, root), "error": str(exc)})
            continue
        if proc.returncode != 0:
            failures.append({"file": rel(source, root), "error": proc.stderr.strip()[-1000:]})
            continue
        try:
            roots = json_stream(proc.stdout)
        except json.JSONDecodeError as exc:
            failures.append({"file": rel(source, root), "error": f"AST JSON parse failed: {exc}"})
            continue
        unit_records: list[dict[str, Any]] = []
        for ast_root in roots:
            collect_records(ast_root, directory, covered, records=unit_records)
        for ast_root in roots:
            collect_edges(ast_root, directory, covered, unit_records, edges=all_edges)
        all_records.extend(unit_records)
        parsed_units += 1

    if parsed_units == 0:
        return {
            "backend": "text-search",
            "reason": "clang AST failed for all covered translation units",
            "compile_commands": rel(database, root),
            "failed_units": failures,
        }
    records = dedupe(all_records, ("qualified_name", "file", "line"))
    edges = dedupe(all_edges, ("from_type", "to_type", "file", "line", "kind"))
    for record in records:
        record["file"] = rel(record["file"], root)
        record.pop("id", None)
    for edge in edges:
        edge["file"] = rel(edge["file"], root)
    return {
        "backend": "clang-ast",
        "clang": clang,
        "compile_commands": rel(database, root),
        "ast_filter": ast_filter,
        "translation_units": parsed_units,
        "failed_units": failures,
        "records": records,
        "semantic_edges": edges,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan C++ semantic dependencies with clang AST")
    parser.add_argument("paths", nargs="+", type=Path, help="Covered C++ source/header files or directories")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--compile-commands", type=Path)
    parser.add_argument("--ast-filter")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    root = args.root.resolve()
    files: set[Path] = set()
    for raw in args.paths:
        path = raw if raw.is_absolute() else root / raw
        if path.is_file():
            files.add(path.resolve())
        elif path.is_dir():
            files.update(item.resolve() for item in path.rglob("*") if item.suffix.lower() in {".h", ".hpp", ".hh", ".cc", ".cpp", ".cxx"})
    result = scan_cpp_semantics(root, sorted(files), args.compile_commands, args.ast_filter, args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("backend") == "clang-ast" else 1


if __name__ == "__main__":
    raise SystemExit(main())
