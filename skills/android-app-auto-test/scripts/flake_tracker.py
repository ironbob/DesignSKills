#!/usr/bin/env python3
"""Flake tracking and quarantine for android-app-auto-test.

A flake is a path whose first attempt failed but passed on retry within the same
batch. Over many batches, paths above the quarantine threshold move to the
"monitor" lane: they keep running but stop blocking the batch.

  record   append one observation per path per run
  recompute rebuild rates[] / lane / quarantined from records
  list     print current rates sorted by flake_rate desc

Typical dispatcher use: after a path is marked flaky, `record`; before each
batch, `recompute`; consult `lane` to decide whether a flaky failure blocks.
"""
import argparse
import datetime as _dt
import json
import pathlib
import sys


def _load(path):
    p = pathlib.Path(path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"records": [], "rates": []}


def _save(path, data):
    pathlib.Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cmd_record(args):
    data = _load(args.flake_tracker)
    data.setdefault("records", []).append(
        {
            "path_id": args.path_id,
            "run_id": args.run_id,
            "first_attempt_failed": args.first_attempt_failed,
            "passed_on_retry": args.passed_on_retry,
            "recorded_at": _now(),
        }
    )
    _save(args.flake_tracker, data)
    sys.stdout.write(
        f"recorded path={args.path_id} run={args.run_id} "
        f"first_failed={args.first_attempt_failed} retry_pass={args.passed_on_retry}\n"
    )


def _recompute(data, threshold, sample_min):
    by_path = {}
    for r in data.get("records", []):
        by_path.setdefault(r["path_id"], []).append(r)
    rates = []
    for path_id, recs in by_path.items():
        sample = len(recs)
        flakes = sum(1 for r in recs if r.get("first_attempt_failed") and r.get("passed_on_retry"))
        rate = flakes / sample if sample else 0.0
        quarantined = sample >= sample_min and rate >= threshold
        rates.append(
            {
                "path_id": path_id,
                "sample_size": sample,
                "flake_count": flakes,
                "flake_rate": round(rate, 4),
                "lane": "monitor" if quarantined else "blocking",
                "quarantined": quarantined,
            }
        )
    rates.sort(key=lambda r: r["flake_rate"], reverse=True)
    data["rates"] = rates
    return data


def cmd_recompute(args):
    data = _load(args.flake_tracker)
    _recompute(data, args.threshold, args.sample_min)
    _save(args.flake_tracker, data)
    quarantined = [r["path_id"] for r in data["rates"] if r["quarantined"]]
    sys.stdout.write(
        f"recomputed {len(data['rates'])} path(s); quarantined={quarantined} "
        f"(threshold={args.threshold}, sample_min={args.sample_min})\n"
    )


def cmd_list(args):
    data = _load(args.flake_tracker)
    if not data.get("rates"):
        # lazily recompute so `list` is useful without an explicit recompute step
        data = _recompute(data, args.threshold, args.sample_min)
    for r in data["rates"]:
        sys.stdout.write(
            f"{r['flake_rate']:.2f}\t{r['lane']}\t"
            f"n={r['sample_size']}\t{r['path_id']}\n"
        )


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="append one flake observation")
    rec.add_argument("flake_tracker")
    rec.add_argument("--path-id", required=True)
    rec.add_argument("--run-id", required=True)
    rec.add_argument("--first-attempt-failed", action="store_true")
    rec.add_argument("--passed-on-retry", dest="passed_on_retry", action="store_true")
    rec.add_argument("--no-passed-on-retry", dest="passed_on_retry", action="store_false")
    rec.set_defaults(passed_on_retry=False)
    rec.set_defaults(func=cmd_record)

    rc = sub.add_parser("recompute", help="rebuild rates/lane/quarantined")
    rc.add_argument("flake_tracker")
    rc.add_argument("--threshold", type=float, default=0.3)
    rc.add_argument("--sample-min", type=int, default=5)
    rc.set_defaults(func=cmd_recompute)

    ls = sub.add_parser("list", help="print current rates")
    ls.add_argument("flake_tracker")
    ls.add_argument("--threshold", type=float, default=0.3)
    ls.add_argument("--sample-min", type=int, default=5)
    ls.set_defaults(func=cmd_list)

    return ap


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
