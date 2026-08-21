#!/usr/bin/env python3
"""Execute contract verification commands without a shell and record evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^VCMD-\d+$")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _tail(value: str, limit: int) -> str:
    return value[-limit:] if len(value) > limit else value


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def fingerprint_inputs(root: Path, inputs: list[str]) -> str:
    """Hash declared repository-relative files/directories and their paths."""
    root = root.resolve()
    files: dict[str, Path] = {}
    total_size = 0
    for value in inputs:
        if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
            raise ValueError(f"verification input must be a safe repository-relative path: {value!r}")
        target = (root / value).resolve()
        if not _inside(root, target) or not target.exists():
            raise ValueError(f"verification input escapes root or does not exist: {value}")
        candidates = [target] if target.is_file() else [item for item in target.rglob("*") if item.is_file()]
        for candidate in candidates:
            resolved = candidate.resolve()
            if not _inside(root, resolved):
                raise ValueError(f"verification input contains an escaping symlink: {candidate}")
            files[resolved.relative_to(root).as_posix()] = resolved
    if not files:
        raise ValueError("verification inputs resolve to no files")
    digest = hashlib.sha256()
    for relative, path in sorted(files.items()):
        total_size += path.stat().st_size
        if len(files) > 10000 or total_size > 100 * 1024 * 1024:
            raise ValueError("verification inputs exceed 10000 files or 100 MiB")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    original_mode = path.stat().st_mode if path.exists() else None
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        if original_mode is not None:
            os.chmod(temp_name, original_mode)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def execute(contract: dict[str, Any], root: Path, only: set[str], tail_chars: int) -> tuple[int, list[str]]:
    verification = contract.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("verification must be an object")
    commands = verification.get("commands")
    if not isinstance(commands, list) or not commands:
        raise ValueError("verification.commands must be a non-empty array")

    failures = 0
    executed_ids: list[str] = []
    known_ids: set[str] = set()
    for command in commands:
        if not isinstance(command, dict):
            raise ValueError("each verification command must be an object")
        command_id = command.get("id")
        if not isinstance(command_id, str) or not ID_RE.fullmatch(command_id) or command_id in known_ids:
            raise ValueError(f"invalid or duplicate command id: {command_id!r}")
        known_ids.add(command_id)
        if only and command_id not in only:
            continue
        argv = command.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
            raise ValueError(f"{command_id}.argv must be a non-empty string array")
        inputs = command.get("inputs")
        if not isinstance(inputs, list) or not inputs:
            raise ValueError(f"{command_id}.inputs must be a non-empty repository-relative path array")
        inputs_sha256 = fingerprint_inputs(root, inputs)
        cwd_value = command.get("cwd", ".")
        if not isinstance(cwd_value, str) or Path(cwd_value).is_absolute():
            raise ValueError(f"{command_id}.cwd must be repository-relative")
        cwd = (root / cwd_value).resolve()
        if not _inside(root, cwd) or not cwd.is_dir():
            raise ValueError(f"{command_id}.cwd escapes root or is not a directory: {cwd_value}")
        timeout = command.get("timeout_seconds", 300)
        if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 3600:
            raise ValueError(f"{command_id}.timeout_seconds must be 1..3600")

        started = time.monotonic()
        executed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            result = subprocess.run(
                argv, cwd=cwd, capture_output=True, text=True, errors="replace",
                timeout=timeout, check=False, shell=False,
            )
            stdout, stderr, exit_code = result.stdout, result.stderr, result.returncode
            status = "passed" if exit_code == 0 else "failed"
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            stderr = (stderr + f"\nTimed out after {timeout}s").strip()
            exit_code, status = None, "failed"
        except OSError as exc:
            stdout, stderr = "", str(exc)
            exit_code, status = None, "failed"
        duration_ms = round((time.monotonic() - started) * 1000)
        command["status"] = status
        command["execution"] = {
            "runner_version": 1,
            "argv_sha256": _digest(json.dumps(argv, ensure_ascii=False, separators=(",", ":"))),
            "inputs_sha256": inputs_sha256,
            "exit_code": exit_code,
            "duration_ms": duration_ms,
            "stdout_sha256": _digest(stdout),
            "stderr_sha256": _digest(stderr),
            "stdout_tail": _tail(stdout, tail_chars),
            "stderr_tail": _tail(stderr, tail_chars),
            "executed_at": executed_at,
        }
        executed_ids.append(command_id)
        if status != "passed" and command.get("required", True):
            failures += 1
        print(f"{command_id}: {status.upper()} ({duration_ms} ms)")

    if only - known_ids:
        raise ValueError(f"unknown --only ids: {sorted(only - known_ids)}")

    status_by_id = {c.get("id"): c.get("status") for c in commands if isinstance(c, dict)}
    for check in verification.get("checks") or []:
        if not isinstance(check, dict):
            continue
        command_ids = check.get("command_ids")
        if not isinstance(command_ids, list) or not command_ids:
            continue
        statuses = [status_by_id.get(item) for item in command_ids]
        if any(status == "failed" for status in statuses):
            check["status"] = "failed"
        elif all(status == "passed" for status in statuses):
            check["status"] = "passed"
        else:
            check["status"] = "pending"
        check["evidence"] = "machine-executed: " + ", ".join(command_ids)
    return failures, executed_ids


def main() -> int:
    parser = argparse.ArgumentParser(description="Run verification commands and record machine evidence")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--execute", action="store_true", help="Required opt-in to execute commands")
    parser.add_argument("--update-contract", action="store_true", help="Atomically write evidence into the contract")
    parser.add_argument("--only", action="append", default=[], metavar="VCMD-N")
    parser.add_argument("--tail-chars", type=int, default=4000)
    args = parser.parse_args()
    if not args.execute:
        parser.error("refusing to run without --execute")
    if not args.contract.exists():
        parser.error(f"contract does not exist: {args.contract}")
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"root is not a directory: {root}")
    if not 0 <= args.tail_chars <= 20000:
        parser.error("--tail-chars must be 0..20000")
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        failures, executed_ids = execute(contract, root, set(args.only), args.tail_chars)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.update_contract:
        _atomic_write(args.contract, contract)
        print(f"updated {args.contract} ({len(executed_ids)} commands)")
    else:
        print("evidence not persisted; pass --update-contract to update the contract")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
