#!/usr/bin/env python3
"""Incremental path selection for android-app-auto-test.

Given a dependency-map.json and a set of changed source files, print the
path_ids that must be rerun (the regression scope for a code change). This is
what makes continuous running affordable: nightly runs the full map, every
commit runs only the affected subset.

Changed files come from any of (in priority order):
  --base <git-ref>        git diff --name-only <base> (default if git available)
  --changed-file <path>   a file listing changed paths, one per line
  --from-stdin            read changed paths from stdin
  (else)                  the whole map's paths (full run fallback)

Usage examples:
  incremental_select.py dep-map.json --base origin/master
  git diff --name-only HEAD~1 | incremental_select.py dep-map.json --from-stdin
  incremental_select.py dep-map.json --changed-file changed.txt \\
      --intersect-run-state run-state.json
"""
import argparse
import json
import pathlib
import subprocess
import sys


def _load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _gather_changed(args):
    if args.changed_file:
        return [
            line.strip()
            for line in pathlib.Path(args.changed_file).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    if args.from_stdin:
        return [line.strip() for line in sys.stdin if line.strip()]
    if args.base is not None:
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", args.base], stderr=subprocess.STDOUT
            )
            return [line.strip() for line in out.decode().splitlines() if line.strip()]
        except Exception as exc:  # not a git repo / bad ref
            sys.stderr.write(f"git diff failed ({exc}); falling back to full map\n")
            return None
    return None


def cmd_select(args):
    dep = _load(args.dependency_map)
    s2p = dep.get("source_to_paths", {}) or {}

    changed = _gather_changed(args)
    if not changed:
        # Full-map fallback: every known path.
        affected = sorted({pid for paths in s2p.values() for pid in paths})
        trigger_note = "full"
    else:
        affected_set = set()
        matched = []
        for f in changed:
            if f in s2p:
                affected_set.update(s2p[f])
                matched.append(f)
        affected = sorted(affected_set)
        trigger_note = "incremental"
        if not matched:
            sys.stderr.write(
                f"no changed file matched dependency-map; changed={changed}\n"
            )

    if args.intersect_run_state:
        rs = _load(args.intersect_run_state)
        keep = {e["path_id"] for e in rs.get("paths", [])}
        affected = [p for p in affected if p in keep]

    for pid in affected:
        sys.stdout.write(pid + "\n")
    sys.stderr.write(f"selected {len(affected)} path(s) ({trigger_note})\n")


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dependency_map")
    ap.add_argument("--base", default=None, help="git ref to diff against, e.g. origin/master")
    ap.add_argument("--changed-file", default=None, help="file listing changed paths")
    ap.add_argument("--from-stdin", action="store_true", help="read changed paths from stdin")
    ap.add_argument(
        "--intersect-run-state",
        default=None,
        help="run-state.json to filter selected paths to the current batch",
    )
    ap.set_defaults(func=cmd_select)
    return ap


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
