#!/usr/bin/env python3
"""Compare serial and bounded-parallel scans and require fact equivalence."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def run(scanner: Path, root: Path, paths: list[str], jobs: int, language: str | None) -> tuple[float, dict]:
    with tempfile.TemporaryDirectory() as temp:
        output = Path(temp) / "scan.json"
        command = [
            sys.executable, str(scanner), *paths, "--root", str(root), "--output", str(output),
            "--scan-jobs", str(jobs), "--cpp-jobs", str(jobs), "--git-history", "0", "--include-tests",
        ]
        if language:
            command.extend(["--language", language])
        started = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        elapsed = time.perf_counter() - started
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout)
        return elapsed, json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark architecture scan equivalence")
    parser.add_argument("paths", nargs="+", help="Module paths relative to --root")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--jobs", type=int, default=min(os.cpu_count() or 1, 4))
    parser.add_argument("--language", choices=("JVM", "C++"))
    args = parser.parse_args()
    scanner = Path(__file__).with_name("scan_architecture.py")
    try:
        serial_time, serial = run(scanner, args.root.resolve(), args.paths, 1, args.language)
        parallel_time, parallel = run(scanner, args.root.resolve(), args.paths, max(1, args.jobs), args.language)
    except RuntimeError as exc:
        sys.stderr.write(f"benchmark_scan: {exc}\n")
        return 2
    equivalent = serial == parallel
    payload = {
        "equivalent": equivalent,
        "serial_seconds": round(serial_time, 6),
        "parallel_seconds": round(parallel_time, 6),
        "speedup": round(serial_time / parallel_time, 3) if parallel_time else None,
        "jobs": max(1, args.jobs),
        "files": len(serial.get("covered_files", [])),
        "edges": serial.get("dependency_edge_count", 0),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())
