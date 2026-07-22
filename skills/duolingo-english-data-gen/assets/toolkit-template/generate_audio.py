#!/usr/bin/env python3
"""Audio generator for a duolingo-english-data-gen toolkit.

Synthesizes English audio for every spoken string under output/ using a pluggable
TTS provider (default: Microsoft Edge TTS). The TTS capability lives in the shared
`tts_providers.py` (consumed via create_provider(), like generate.py consumes ai_bridge).

Spoken strings covered:
  - lesson exercises with audio_ref + target_sentence (listening / speaking) -> audio/<id>.mp3
  - listening slow_audio_ref + target_sentence -> a second clip at config.tts.slow_rate
  - picture option objects with text + audio_ref -> target-word pronunciation
  - character_dialogue exercise turns[].text_en -> audio/turn_<n>.mp3 (voice per cast character)
  - duoradio episode turns[].text_en -> audio/turn_<n>.mp3 (voice per cast character)

The inline audio_ref path is written back into the JSON so build_android_assets carries
it into the app bundle. mp3 files land next to the JSON under output/<cefr>/<id>/audio/.

⚠ CROSS-REPO IMPORT: tts_providers.py may live in a DIFFERENT repo than this toolkit
(e.g. toolkit under DesignSkills, tts_providers under LearnEnglish). The upward walk
will not cross that boundary, so set one of (checked in priority order):
    DUOLINGO_TTS_ROOT  >  TTS_PROVIDERS_ROOT  >  EDU_DATA_GEN_ROOT
to the directory containing tts_providers.py. If unresolved, FAIL FAST.

Resumable / idempotent (no state file): a clip is skipped when its mp3 already exists
with non-zero size. Per-clip retry with backoff. Atomic JSON write.

Usage:
  python3 generate_audio.py                     # all lessons + duoradio, all CEFR
  python3 generate_audio.py --cefr A1
  python3 generate_audio.py --only lesson-a1-1-1-hi
  python3 generate_audio.py --sample 3
  python3 generate_audio.py --force
  python3 generate_audio.py --dry-run
  python3 generate_audio.py --provider edge --voice-default en-US-AriaNeural
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import sys
from pathlib import Path


KNOWN_TTS_PATH = "/Volumes/JINGZAO/work_space/LearnEnglish/tts_providers.py"


# ---------------------------------------------------------------------------
# Locate tts_providers.py: upward walk + env escape hatches (cross-repo).
# ---------------------------------------------------------------------------
def _ensure_tts_providers() -> None:
    if "tts_providers" in sys.modules:
        return
    candidates: list[Path] = []
    for env_var in ("DUOLINGO_TTS_ROOT", "TTS_PROVIDERS_ROOT", "EDU_DATA_GEN_ROOT"):
        env_root = os.environ.get(env_var)
        if env_root and Path(env_root, "tts_providers.py").exists():
            candidates.append(Path(env_root))
            break
    if not candidates:
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            if (parent / "tts_providers.py").exists():
                candidates.append(parent)
                break
    for root in candidates:
        r = str(root)
        if r not in sys.path:
            sys.path.insert(0, r)
    try:
        import tts_providers  # noqa: F401
    except ImportError as e:  # pragma: no cover
        sys.exit(
            f"[generate_audio] cannot import tts_providers: {e}.\n"
            f"It was not found by upward walk. Set one of "
            f"DUOLINGO_TTS_ROOT / TTS_PROVIDERS_ROOT / EDU_DATA_GEN_ROOT to the dir "
            f"containing tts_providers.py (known path: {KNOWN_TTS_PATH})."
        )


_ensure_tts_providers()

from tts_providers import create_provider  # noqa: E402


# ---------------------------------------------------------------------------
# IO helpers
# ---------------------------------------------------------------------------

def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write_json_atomic(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def discover_files(output_dir: Path) -> list[Path]:
    """All lesson.json + duoradio.json under output/<cefr>/<id>/ (skip _meta)."""
    files: list[Path] = []
    if not output_dir.exists():
        return files
    for path in output_dir.rglob("*.json"):
        if path.name in ("_meta.json", "cast.json"):
            continue
        if path.name in ("lesson.json", "duoradio.json"):
            files.append(path)
    files.sort()
    return files


def load_cast(tk_root: Path, config: dict) -> dict[str, str]:
    """character_id -> voice, from cast.json."""
    cast_file = tk_root / config.get("paths", {}).get("cast_file", "cast.json")
    voice_map: dict[str, str] = {}
    if cast_file.exists():
        try:
            data = load_json(cast_file)
            for c in (data or {}).get("characters") or []:
                if c.get("id") and c.get("voice"):
                    voice_map[c["id"]] = c["voice"]
        except Exception:
            pass
    return voice_map


# ---------------------------------------------------------------------------
# Job planning
# ---------------------------------------------------------------------------

def _speaker_voice_lookup(turns: list, cast_voice: dict, voice_a: str, voice_b: str, default_voice: str):
    """1st distinct character_id -> voice_a, 2nd -> voice_b, others alternate.
    If a turn's character_id has a cast voice, prefer it."""
    order: dict[str, str] = {}

    def assign(char_id: str) -> str:
        if char_id in cast_voice:
            return cast_voice[char_id]
        if char_id not in order:
            if len(order) == 0:
                order[char_id] = voice_a
            elif len(order) == 1:
                order[char_id] = voice_b
            else:
                order[char_id] = voice_a if len(order) % 2 == 0 else voice_b
        return order[char_id]

    def lookup(turn: dict) -> str:
        cid = turn.get("character_id") or turn.get("speaker") or ""
        return assign(cid) if cid else default_voice

    return lookup


def plan_jobs(obj: dict, obj_dir: Path, cfg: dict, cast_voice: dict) -> list[dict]:
    """Build synth jobs for one lesson.json or duoradio.json."""
    default_voice = cfg["default_voice"]
    voice_a = cfg["voice_a"]
    voice_b = cfg["voice_b"]
    audio_dir = obj_dir / "audio"
    jobs: list[dict] = []

    def add(kind: str, loc: dict, field: str, text: str, filename: str, voice: str,
            rate: str | None = None) -> None:
        rel = f"audio/{filename}"
        jobs.append({"kind": kind, "loc": loc, "field": field, "text": text,
                     "out": audio_dir / filename, "rel": rel, "voice": voice,
                     "rate": rate or cfg["rate"]})

    # lesson: iterate exercises
    for ex in obj.get("exercises") or []:
        if not isinstance(ex, dict):
            continue
        exid = ex.get("id", "ex")
        # exercise-level audio (listening/speaking types carry audio_ref + target_sentence)
        ref = ex.get("audio_ref")
        ts = (ex.get("target_sentence") or "").strip()
        if ref and ts:
            fname = ref.split("/")[-1] if ref.startswith("audio/") else f"{exid}.mp3"
            add("exercise", ex, "audio_ref", ts, fname, default_voice)
        slow_ref = ex.get("slow_audio_ref")
        if slow_ref and ts:
            fname = slow_ref.split("/")[-1] if slow_ref.startswith("audio/") else f"{exid}-slow.mp3"
            add("exercise-slow", ex, "slow_audio_ref", ts, fname, default_voice,
                cfg["slow_rate"])
        # Picture-choice vocabulary pronunciation lives on each structured option.
        for i, option in enumerate(ex.get("options") or [], 1):
            if not isinstance(option, dict):
                continue
            option_ref = option.get("audio_ref")
            option_text = (option.get("text") or "").strip()
            if option_ref and option_text:
                fname = (option_ref.split("/")[-1] if option_ref.startswith("audio/")
                         else f"{exid}-option-{i}.mp3")
                add("option", option, "audio_ref", option_text, fname, default_voice)
        # character_dialogue turns
        turns = ex.get("turns") or []
        if turns:
            voice_of = _speaker_voice_lookup(turns, cast_voice, voice_a, voice_b, default_voice)
            for i, t in enumerate(turns):
                if not isinstance(t, dict):
                    continue
                text = (t.get("text_en") or "").strip()
                if text:
                    ref = t.get("audio_ref") or f"audio/{exid}-turn-{i+1}.mp3"
                    fname = ref.split("/")[-1] if ref.startswith("audio/") else f"{exid}-turn-{i+1}.mp3"
                    add("turn", t, "audio_ref", text, fname, voice_of(t))

    # duoradio: top-level turns
    turns = obj.get("turns") or []
    if turns:
        voice_of = _speaker_voice_lookup(turns, cast_voice, voice_a, voice_b, default_voice)
        for i, t in enumerate(turns):
            if not isinstance(t, dict):
                continue
            text = (t.get("text_en") or "").strip()
            if text:
                oid = obj.get("id", "radio")
                ref = t.get("audio_ref") or f"audio/{oid}-turn-{i+1}.mp3"
                fname = ref.split("/")[-1] if ref.startswith("audio/") else f"{oid}-turn-{i+1}.mp3"
                add("turn", t, "audio_ref", text, fname, voice_of(t))

    return jobs


# ---------------------------------------------------------------------------
# Synthesis (one clip): idempotent + retry
# ---------------------------------------------------------------------------

async def synth_one(provider, job: dict, max_retries: int,
                    force: bool, sem: asyncio.Semaphore) -> tuple[str, str | None]:
    out: Path = job["out"]
    if not force and out.exists() and out.stat().st_size > 0:
        # still ensure the inline ref is set (idempotent)
        if job["loc"].get(job["field"]) != job["rel"]:
            job["loc"][job["field"]] = job["rel"]
        return "skip", None
    out.parent.mkdir(parents=True, exist_ok=True)
    async with sem:
        last_err = None
        for attempt in range(1, max_retries + 1):
            try:
                await provider.synthesize(job["text"], str(out), voice=job["voice"], rate=job["rate"])
                if out.exists() and out.stat().st_size > 0:
                    job["loc"][job["field"]] = job["rel"]
                    return "ok", None
                last_err = "provider returned empty audio"
            except Exception as e:  # transient
                last_err = f"{type(e).__name__}: {e}"
                if out.exists() and out.stat().st_size == 0:
                    out.unlink(missing_ok=True)
            if attempt < max_retries:
                await asyncio.sleep(min(2 ** attempt, 8))
    if out.exists() and out.stat().st_size == 0:
        out.unlink(missing_ok=True)
    return "fail", last_err


# ---------------------------------------------------------------------------
# Per-file orchestration
# ---------------------------------------------------------------------------

async def process_file(path: Path, provider, cfg: dict, cast_voice: dict,
                       force: bool, dry_run: bool, sem: asyncio.Semaphore) -> dict:
    obj = load_json(path)
    obj_dir = path.parent
    jobs = plan_jobs(obj, obj_dir, cfg, cast_voice)
    fid = obj.get("id", obj_dir.name)
    if not jobs:
        return {"id": fid, "planned": 0, "ok": 0, "skip": 0, "fail": 0, "written": False}
    if dry_run:
        return {"id": fid, "planned": len(jobs), "ok": 0, "skip": 0, "fail": 0, "written": False, "dry": True}

    max_retries = cfg["max_retries"]
    results = await asyncio.gather(
        *(synth_one(provider, j, max_retries, force, sem) for j in jobs))
    ok = skip = fail = 0
    first_err = None
    for job, (status, err) in zip(jobs, results):
        if status == "ok":
            ok += 1
        elif status == "skip":
            skip += 1
        else:
            fail += 1
            if first_err is None:
                first_err = f"{job['rel']}: {err}"
    if ok or skip:  # refs mutated in place → persist
        write_json_atomic(path, obj)
    return {"id": fid, "planned": len(jobs), "ok": ok, "skip": skip,
            "fail": fail, "written": bool(ok or skip), "err": first_err}


async def run_all(paths, provider, cfg, cast_voice, force, dry_run, sem) -> None:
    tp = tok = tsk = tf = tw = 0
    n = len(paths)
    for i, path in enumerate(paths, 1):
        r = await process_file(path, provider, cfg, cast_voice, force, dry_run, sem)
        tp += r["planned"]; tok += r["ok"]; tsk += r["skip"]; tf += r["fail"]
        tw += 1 if r.get("written") else 0
        if dry_run:
            print(f"  [plan] {r['id']:32s} {r['planned']:2d} clip(s)")
        else:
            flag = f"  ✗ {r['fail']} failed ({r.get('err')})" if r["fail"] else ""
            print(f"  [{i}/{n}] {r['id']:32s} ok={r['ok']} skip={r['skip']} fail={r['fail']}{flag}")
    print(f"\n[generate_audio] files={n} clips: planned={tp} ok={tok} skip={tsk} fail={tf} json_written={tw}")


# ---------------------------------------------------------------------------
# Selection + CLI
# ---------------------------------------------------------------------------

def select_paths(paths: list[Path], args) -> list[Path]:
    items = list(paths)
    if args.cefr:
        # output/<cefr>/<id>/<file> → parent.parent.name == cefr
        items = [p for p in items if p.parent.parent.name.lower() == args.cefr.lower()]
    if args.only:
        wanted = set(args.only.split(","))
        items = [p for p in items if p.parent.name in wanted]
        return items
    if args.sample:
        rng = random.Random(args.seed or 0)
        items = rng.sample(items, min(args.sample, len(items))) if items else []
    elif args.limit:
        items = items[: args.limit]
    return items


def merge_cfg(config: dict, args) -> dict:
    tts = dict(config.get("tts", {}))
    for attr, key in (("provider", "provider"), ("voice_default", "default_voice"),
                      ("voice_a", "voice_a"), ("voice_b", "voice_b"), ("rate", "rate"),
                      ("slow_rate", "slow_rate"),
                      ("concurrency", "concurrency")):
        val = getattr(args, attr, None)
        if val is not None:
            tts[key] = val
    if args.max_retries is not None:
        tts["max_retries"] = args.max_retries
    tts.setdefault("provider", "edge")
    tts.setdefault("default_voice", "en-US-AriaNeural")
    tts.setdefault("voice_a", "en-US-AriaNeural")
    tts.setdefault("voice_b", "en-US-GuyNeural")
    tts.setdefault("rate", "-5%")
    tts.setdefault("slow_rate", "-30%")
    tts.setdefault("concurrency", 8)
    tts.setdefault("max_retries", 3)
    return tts


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate TTS audio for duolingo-style lessons.")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--root", default=None)
    ap.add_argument("--cefr", default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--provider", default=None)
    ap.add_argument("--voice-default", dest="voice_default", default=None)
    ap.add_argument("--voice-a", dest="voice_a", default=None)
    ap.add_argument("--voice-b", dest="voice_b", default=None)
    ap.add_argument("--rate", default=None)
    ap.add_argument("--slow-rate", dest="slow_rate", default=None)
    ap.add_argument("--concurrency", type=int, default=None)
    ap.add_argument("--max-retries", dest="max_retries", type=int, default=None)
    args = ap.parse_args()

    tk_root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    config = load_json(tk_root / args.config)
    cfg = merge_cfg(config, args)
    output_dir = tk_root / config.get("paths", {}).get("output_dir", "output")
    cast_voice = load_cast(tk_root, config)
    paths = select_paths(discover_files(output_dir), args)

    cefr_tag = f" [cefr={args.cefr}]" if args.cefr else ""
    mode = "DRY-RUN" if args.dry_run else ("FORCE" if args.force else "resume")
    print(f"[generate_audio]{cefr_tag} provider={cfg['provider']} "
          f"voice_default={cfg['default_voice']} rate={cfg['rate']} slow_rate={cfg['slow_rate']} "
          f"concurrency={cfg['concurrency']} cast_chars={len(cast_voice)} mode={mode}")
    print(f"[generate_audio] {len(paths)} file(s) selected under {output_dir}")
    if not paths:
        return 0

    provider = create_provider(cfg["provider"])
    sem = asyncio.Semaphore(int(cfg["concurrency"]))
    asyncio.run(run_all(paths, provider, cfg, cast_voice, args.force, args.dry_run, sem))
    return 0


if __name__ == "__main__":
    sys.exit(main())
