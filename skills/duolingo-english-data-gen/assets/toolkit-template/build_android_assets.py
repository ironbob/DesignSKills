#!/usr/bin/env python3
"""Bundle generated duolingo-style course data into Android app assets.

Reads output/<cefr>/<id>/{lesson,duoradio}.json + each audio/ dir, plus cast.json,
and writes a self-contained asset tree the Android app can consume:
  <asset_root>/<cefr>.json          consolidated per-CEFR array of lessons/episodes
  <asset_root>/audio/<cefr>/<id>/*  copied mp3s
  <asset_root>/cast.json            original character cast
  <asset_root>/manifest.json        index of all lessons/episodes by CEFR

NOTE: exact alignment with the app's existing consumption format is a documented
follow-up (see requirements 未决问题). This follows the daily-expression-toolkit
convention and DOES copy audio (closing the gap that toolkit's build script left open).

Usage:
  python build_android_assets.py --root <toolkit> [--asset-root android/app/src/main/assets/duolingo_english]
  python build_android_assets.py --root <toolkit --cefr A1 --force
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def discover(output_dir: Path):
    """Yield (cefr, id, kind, file_path) for every lesson.json / duoradio.json."""
    found = []
    if not output_dir.exists():
        return found
    for path in sorted(output_dir.rglob("*.json")):
        if path.name not in ("lesson.json", "duoradio.json"):
            continue
        cefr = path.parent.parent.name
        cid = path.parent.name
        kind = "lesson" if path.name == "lesson.json" else "duoradio_episode"
        found.append((cefr, cid, kind, path))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="Bundle duolingo-style course data into Android assets.")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--root", default=None, help="toolkit root dir (default: cwd)")
    ap.add_argument("--asset-root", default=None,
                    help="asset output dir (default: <root>/android/app/src/main/assets/duolingo_english)")
    ap.add_argument("--cefr", default=None, help="only this CEFR")
    ap.add_argument("--force", action="store_true", help="overwrite existing asset tree")
    args = ap.parse_args()

    tk_root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    config = load_json(tk_root / args.config)
    output_dir = tk_root / config["paths"]["output_dir"]
    asset_root = Path(args.asset_root).resolve() if args.asset_root else (
        tk_root / "android" / "app" / "src" / "main" / "assets" / "duolingo_english")

    if asset_root.exists() and not args.force:
        print(f"[build_android_assets] {asset_root} 已存在；用 --force 覆盖")
        return 1
    if asset_root.exists():
        shutil.rmtree(asset_root)
    asset_root.mkdir(parents=True, exist_ok=True)

    items = discover(output_dir)
    if args.cefr:
        items = [it for it in items if it[0].lower() == args.cefr.lower()]

    by_cefr: dict[str, list] = {}
    manifest = {"course": config.get("product", {}).get("name", ""), "cefr": {}}
    n_audio = 0

    for cefr, cid, kind, path in items:
        obj = load_json(path)
        # strip heavy/derived fields if any; keep exercises + meta
        by_cefr.setdefault(cefr, []).append(obj)
        manifest["cefr"].setdefault(cefr, {"lessons": [], "duoradio": []})
        bucket = "lessons" if kind == "lesson" else "duoradio"
        manifest["cefr"][cefr][bucket].append({"id": cid, "title": obj.get("title", "")})
        # copy audio
        audio_src = path.parent / "audio"
        if audio_src.exists():
            audio_dst = asset_root / "audio" / cefr / cid
            audio_dst.mkdir(parents=True, exist_ok=True)
            for mp3 in audio_src.glob("*.mp3"):
                shutil.copy2(mp3, audio_dst / mp3.name)
                n_audio += 1

    # cast
    cast_file = tk_root / config.get("paths", {}).get("cast_file", "cast.json")
    if cast_file.exists():
        write_json(asset_root / "cast.json", load_json(cast_file))

    # per-CEFR consolidated + manifest
    for cefr, arr in by_cefr.items():
        write_json(asset_root / f"{cefr}.json", arr)
    write_json(asset_root / "manifest.json", manifest)

    total = sum(len(v) for v in by_cefr.values())
    print(f"[build_android_assets] bundled {total} item(s) across {sorted(by_cefr)} "
          f"+ {n_audio} audio clip(s) → {asset_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
