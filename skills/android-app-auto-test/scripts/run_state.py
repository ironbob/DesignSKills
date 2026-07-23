#!/usr/bin/env python3
"""Batch run-state machine for android-app-auto-test.

run-state.json is the single source of truth for a resumable batch. Each
confirmed path transitions:

    pending -> running -> {passed|failed|blocked|flaky|skipped}

The dispatcher loop is:

    pid=$(run_state.py next-pending run-state.json)   # claims + prints one id
    ... run/fix the path ...
    run_state.py mark run-state.json "$pid" passed --run-id ...

State is on disk, so any session resumes by reloading run-state.json. A single
dispatcher owns a run-state.json at a time (one path per device); there is no
cross-process locking.
"""
import argparse
import datetime as _dt
import json
import pathlib
import sys

STATUSES = ["pending", "running", "passed", "failed", "blocked", "flaky", "skipped"]
TERMINAL = {"passed", "failed", "blocked", "flaky", "skipped"}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def _load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def _save(path, state):
    pathlib.Path(path).write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recompute_progress(state):
    counts = {k: 0 for k in STATUSES}
    for entry in state.get("paths", []):
        s = entry.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1
    state["progress"] = counts
    return state


def _select(paths, scope):
    scope = scope or {}
    stype = scope.get("scope_type")
    if not stype or stype == "all_confirmed_p0":
        p0 = [p for p in paths if p.get("priority") == "P0"]
        return p0 if p0 else list(paths)
    if stype == "priorities":
        wanted = set(scope.get("priorities", []))
        return [p for p in paths if p.get("priority") in wanted]
    if stype == "path_ids":
        wanted = set(scope.get("path_ids", []))
        return [p for p in paths if p.get("path_id") in wanted]
    if stype in ("feature", "module"):
        key = scope.get("feature") or scope.get("module") or ""
        return [p for p in paths if key in (p.get("path_id", ""), p.get("goal", ""))] or list(paths)
    # test_file/test_class/test_package/gradle_command: keep whole map; the
    # test-plan narrows at execution time.
    return list(paths)


def print_progress(state):
    p = state.get("progress", {})
    total = len(state.get("paths", []))
    done = sum(p.get(s, 0) for s in TERMINAL)
    sys.stdout.write(
        "progress: "
        + " ".join(f"{k}={p.get(k, 0)}" for k in STATUSES)
        + f" total={total} done={done}\n"
    )


def cmd_init(args):
    pm = _load(args.from_path_map)
    inputs = _load(args.from_inputs) if args.from_inputs else {}
    scope = inputs.get("test_scope", {}) or {}
    selected = _select(pm.get("paths", []), scope)
    state = {
        "batch_id": args.batch_id or _now(),
        "created_at": _now(),
        "scope": scope,
        "non_interactive": bool(inputs.get("non_interactive", False)),
        "max_fix_attempts": int(inputs.get("max_fix_attempts", 3)),
        "regression_on_fix": bool(inputs.get("regression_on_fix", True)),
        "flake_policy": inputs.get(
            "flake_policy", {"retries": 1, "quarantine_threshold": 0.3, "sample_min": 5}
        ),
        "paths": [
            {
                "path_id": p["path_id"],
                "priority": p.get("priority"),
                "status": "pending",
                "attempts": 0,
                "fix_attempts": 0,
                "last_run_id": None,
                "last_failure_id": None,
                "updated_at": None,
                "blocked_reason": None,
            }
            for p in selected
        ],
    }
    _recompute_progress(state)
    _save(args.run_state, state)
    print_progress(state)


def _find(state, path_id):
    for entry in state.get("paths", []):
        if entry["path_id"] == path_id:
            return entry
    raise SystemExit(f"path_id not found in run-state: {path_id}")


def cmd_next_pending(args):
    state = _load(args.run_state)
    index = {e["path_id"]: i for i, e in enumerate(state["paths"])}
    pending = [e for e in state["paths"] if e["status"] == "pending"]
    if not pending:
        print("")
        return
    pending.sort(key=lambda e: (PRIORITY_ORDER.get(e.get("priority"), 9), index[e["path_id"]]))
    entry = pending[0]
    entry["status"] = "running"
    entry["updated_at"] = _now()
    _recompute_progress(state)
    _save(args.run_state, state)
    print(entry["path_id"])


def cmd_mark(args):
    if args.status not in TERMINAL and args.status != "pending":
        raise SystemExit(f"invalid status: {args.status}")
    state = _load(args.run_state)
    entry = _find(state, args.path_id)
    entry["status"] = args.status
    entry["updated_at"] = _now()
    if args.run_id:
        entry["last_run_id"] = args.run_id
    if args.failure_id:
        entry["last_failure_id"] = args.failure_id
    if args.attempts is not None:
        entry["attempts"] = args.attempts
    if args.fix_attempts is not None:
        entry["fix_attempts"] = args.fix_attempts
    if args.blocked_reason:
        entry["blocked_reason"] = args.blocked_reason
    _recompute_progress(state)
    _save(args.run_state, state)
    print_progress(state)


def cmd_reset(args):
    state = _load(args.run_state)
    targets = set(args.statuses) if args.statuses else {"failed", "blocked", "flaky"}
    n = 0
    for entry in state["paths"]:
        if entry["status"] in targets:
            entry["status"] = "pending"
            entry["fix_attempts"] = 0
            entry["blocked_reason"] = None
            entry["updated_at"] = _now()
            n += 1
    _recompute_progress(state)
    _save(args.run_state, state)
    sys.stdout.write(f"reset {n} paths to pending\n")


def cmd_progress(args):
    print_progress(_load(args.run_state))


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="create run-state.json from path-map.json + inputs.json")
    i.add_argument("run_state")
    i.add_argument("--from-path-map", required=True)
    i.add_argument("--from-inputs")
    i.add_argument("--batch-id")
    i.set_defaults(func=cmd_init)

    n = sub.add_parser("next-pending", help="claim and print the next pending path_id (empty if none)")
    n.add_argument("run_state")
    n.set_defaults(func=cmd_next_pending)

    m = sub.add_parser("mark", help="set a path's status")
    m.add_argument("run_state")
    m.add_argument("path_id")
    m.add_argument("status", choices=STATUSES)
    m.add_argument("--run-id")
    m.add_argument("--failure-id")
    m.add_argument("--attempts", type=int)
    m.add_argument("--fix-attempts", type=int)
    m.add_argument("--blocked-reason")
    m.set_defaults(func=cmd_mark)

    r = sub.add_parser("reset", help="return failed/blocked/flaky to pending for a rerun pass")
    r.add_argument("run_state")
    r.add_argument("--statuses", nargs="*", default=None)
    r.set_defaults(func=cmd_reset)

    pr = sub.add_parser("progress", help="print the progress summary")
    pr.add_argument("run_state")
    pr.set_defaults(func=cmd_progress)

    return ap


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
