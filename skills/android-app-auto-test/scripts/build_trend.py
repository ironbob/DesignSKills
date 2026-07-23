#!/usr/bin/env python3
"""Append a cross-batch trend entry for android-app-auto-test.

One history entry per finished batch, derived from run-state progress and the
coverage dimensions. The report-writer renders docs/android-test/trend-report.md
from trend.json; this script only appends the data point.

  build_trend.py trend.json \
      --run-state run-state.json \
      --coverage coverage.json \
      --trigger nightly|incremental|manual \
      [--duration-seconds N] [--batch-id ...] [--finished-at ISO]
"""
import argparse
import datetime as _dt
import json
import pathlib
import sys

TERMINAL = {"passed", "failed", "blocked", "flaky", "skipped"}


def _load(path):
    p = pathlib.Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _save(path, data):
    pathlib.Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _from_run_state(rs):
    progress = rs.get("progress", {}) or {}
    entry = {k: int(progress.get(k, 0)) for k in ("passed", "failed", "blocked", "flaky", "skipped")}
    entry["total"] = len(rs.get("paths", []))
    entry["batch_id"] = rs.get("batch_id")
    return entry


def _feature_coverage(cov):
    feat = {}
    for f in cov.get("by_feature", []) or []:
        total = f.get("total", 0) or 0
        ratio = f.get("coverage_ratio")
        if ratio is None and total:
            ratio = round((f.get("passed", 0)) / total, 4)
        feat[f.get("feature_id", "?")] = ratio
    return feat


def cmd_append(args):
    trend = _load(args.trend)
    trend.setdefault("history", [])

    rs = _load(args.run_state) if args.run_state else {}
    cov = _load(args.coverage) if args.coverage else {}

    counts = _from_run_state(rs) if rs else {k: 0 for k in (*TERMINAL, "total")}
    entry = {
        "batch_id": args.batch_id or counts.get("batch_id") or _now(),
        "finished_at": args.finished_at or _now(),
        "trigger": args.trigger,
        "total": counts.get("total", 0),
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0),
        "blocked": counts.get("blocked", 0),
        "flaky": counts.get("flaky", 0),
        "duration_seconds": args.duration_seconds,
        "feature_coverage": _feature_coverage(cov),
    }
    trend["history"].append(entry)
    _save(args.trend, trend)
    sys.stdout.write(
        f"appended trend entry batch={entry['batch_id']} "
        f"passed={entry['passed']}/{entry['total']} trigger={entry['trigger']}\n"
    )


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("trend")
    ap.add_argument("--run-state", default=None)
    ap.add_argument("--coverage", default=None)
    ap.add_argument("--trigger", default="manual")
    ap.add_argument("--duration-seconds", type=int, default=None)
    ap.add_argument("--batch-id", default=None)
    ap.add_argument("--finished-at", default=None)
    ap.set_defaults(func=cmd_append)
    return ap


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
