#!/usr/bin/env python3
"""Data-generation engine for a duolingo-english-data-gen toolkit.

Resumable / retrying / idempotent generator. Calls the LLM via ai_bridge
(provider `claude_code` → ClaudeCodeDirectProvider). Generation unit = ONE
LESSON: a single LLM call returns an ordered exercise array (12-17 exercises
following a curve_plan). Each lesson → one atomic file.

Capabilities:
  - 中断/恢复 (interrupt/resume): progress persisted to state/state.json; reruns skip done lessons.
  - 重试 (retry): per-lesson retries up to config.llm.max_retries on LLM/parse error.
  - 幂等 (idempotent): done lessons skipped unless --force.
  - 单文件原子课 (single-file-per-lesson): one lesson = one file with ALL exercises + meta.
  - 目标句锁定 (target-lock): _post_process re-injects locked targets + structural metadata.

Usage:
  python generate.py                       # generate all pending lessons (all CEFR)
  python generate.py --cefr A1            # only one CEFR's lessons
  python generate.py --limit 5            # only next 5 pending
  python generate.py --sample 3           # random sample of 3 pending
  python generate.py --only id1,id2       # specific ids (implies --force for those)
  python generate.py --force              # regenerate even done lessons
  python generate.py --dry-run            # plan only, no LLM calls

Exits non-zero only on auth/config errors; per-lesson failures go to state.failed (resumable).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Locate ai_bridge: walk up from this script to find a dir containing ai_bridge/.
# (Toolkits live inside the DesignSkills repo so ai_bridge is reachable upward;
# override with env EDU_DATA_GEN_ROOT or PYTHONPATH if relocated.)
# ---------------------------------------------------------------------------
def _ensure_ai_bridge() -> None:
    if "ai_bridge" in sys.modules:
        return
    env_root = os.environ.get("EDU_DATA_GEN_ROOT")
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root))
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / "ai_bridge" / "__init__.py").exists():
            candidates.append(parent)
            break
    for root in candidates:
        r = str(root)
        if r not in sys.path:
            sys.path.insert(0, r)
    try:
        import ai_bridge  # noqa: F401
    except ImportError as e:  # pragma: no cover
        sys.exit(
            f"[generate] cannot import ai_bridge: {e}. "
            f"Set EDU_DATA_GEN_ROOT to the DesignSkills repo root."
        )


_ensure_ai_bridge()

from ai_bridge import AIBridge  # noqa: E402
from ai_bridge.exceptions import (  # noqa: E402
    AuthenticationError,
    NetworkError,
    ProviderError,
    RateLimitError,
)


BLOOM_LABELS = {
    "remember": "记忆(再认/回忆)",
    "understand": "理解(解释/归纳)",
    "apply": "应用(在新情境使用)",
}

VALID_ENTITIES = {"lesson", "duoradio_episode"}

# authoritative field that holds a locked target, per exercise_type
_TARGET_FIELD = {
    "translate": "target_sentence", "complete_translation": "target_sentence",
    "arrange_words": "target_sentence", "sentence_shuffle": "target_sentence",
    "type_what_you_hear": "target_sentence", "what_do_you_hear": "target_sentence",
    "speak_this_sentence": "target_sentence",
    "mark_meaning": "source_text", "select_missing_word": "source_text",
    "read_and_respond": "source_text",
}


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


def load_state(state_file: Path) -> dict:
    if state_file.exists():
        return load_json(state_file)
    return {"done": {}, "failed": {}}


def save_state(state_file: Path, state: dict) -> None:
    write_json_atomic(state_file, state)


def load_content_list(tk_root: Path, config: dict, cefr: str | None = None) -> list:
    """Load content points from config.paths.content_list (per-CEFR dir:
    content_list/a1.json …; *.example.json skipped). With --cefr, only that level."""
    cl = tk_root / config["paths"]["content_list"]
    items: list = []
    if cl.is_dir():
        files = sorted(f for f in cl.glob("*.json") if not f.name.endswith(".example.json"))
        if cefr:
            files = [f for f in files if f.stem == cefr.lower()]
        for f in files:
            data = load_json(f)
            if isinstance(data, list):
                items.extend(data)
    elif cl.is_file():
        items = load_json(cl)
    else:
        raise FileNotFoundError(f"content_list not found: {cl}")
    if cefr:
        items = [c for c in items if (c.get("cefr") or "").upper() == cefr.upper()]
    return items


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def slugify(content_point_id: str) -> str:
    parts = content_point_id.split("-")
    return parts[-1] if parts else content_point_id


def render_template(template: str, context: dict) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        val = context.get(key, "")
        if isinstance(val, (dict, list)):
            return json.dumps(val, ensure_ascii=False, indent=2)
        return str(val)

    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", repl, template)


def resolve_curve_plan(cp: dict, config: dict) -> dict:
    """Resolve a lesson's curve_plan: explicit on the content point, else inherit
    config.curve_defaults[cefr]. Returns {} if unresolvable (gate will flag)."""
    cp_plan = cp.get("curve_plan") or (cp.get("seed") or {}).get("curve_plan")
    if isinstance(cp_plan, dict) and cp_plan.get("stages"):
        return cp_plan
    cefr = (cp.get("cefr") or "").upper()
    defaults = config.get("curve_defaults", {})
    by_level = {str(k).upper(): v for k, v in defaults.items()}
    inherited = by_level.get(cefr)
    if isinstance(inherited, dict) and inherited.get("stages"):
        return inherited
    return {}


def _translation_strategy(cefr: str) -> str:
    if cefr in ("A1", "A2"):
        return (f"本课为低阶（{cefr}），**必须带中文**：每道练习的 `hint_zh` 或翻译题的中文释义不得为空；"
                f"翻译题可双向（direction 用 en2zh 与 zh2en）。让中文母语者能借助中文理解。"
                f"translate 题至少给出中文参考；choice 类可用中文选项帮助识别。")
    return (f"本课为高阶（{cefr}），**no-translation 沉浸式**：用英文释义学新词，不得把整句/整义翻成中文"
            f"（meaning_zh 必须为空）；仅允许短 `hint_zh` 作提示（可选，且不是完整释义）。"
            f"翻译题只做 en2en 释义或英文复述，不出现中文整义。")


def build_context(cp: dict, schema_json, prompt_version: str, config: dict) -> dict:
    cefr = (cp.get("cefr") or config["product"].get("default_cefr", "A1")).upper()
    seed = cp.get("seed") or {}
    ctx = {
        "cefr_translation_strategy": _translation_strategy(cefr),
        "entity": cp.get("entity", "lesson"),
        "id": cp.get("id", ""),
        "cefr": cefr,
        "section_id": cp.get("section_id", ""),
        "unit_id": cp.get("unit_id", ""),
        "title": (seed.get("title") or cp.get("title") or ""),
        "curve_plan": resolve_curve_plan(cp, config),
        "locked_targets": seed.get("locked_targets") or cp.get("locked_targets") or [],
        "target_vocab": seed.get("target_vocab") or cp.get("target_vocab") or [],
        "character_dialogue_hook": seed.get("character_dialogue_hook") or cp.get("character_dialogue_hook") or {},
        "seed_json": seed,
        "schema_json": schema_json or {},
        "product_name": config["product"].get("name", ""),
        "subject": config["product"].get("subject", "en"),
        "prompt_version": prompt_version,
    }
    for k, v in seed.items():  # flatten seed.* so {{seed.foo}} works
        ctx.setdefault(f"seed.{k}", v)
    return ctx


# ---------------------------------------------------------------------------
# JSON extraction (supports top-level {…} or […] — the array fix)
# ---------------------------------------------------------------------------

def extract_json(text: str):
    """Strip code fences / prose, parse the first JSON object OR array."""
    if text is None:
        raise ValueError("empty model output")
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", s, re.S)
    if fence:
        s = fence.group(1)
    else:
        # find first { or [
        idx_obj = s.find("{")
        idx_arr = s.find("[")
        cands = [i for i in (idx_obj, idx_arr) if i != -1]
        if not cands:
            raise ValueError("no JSON object/array found in model output")
        start = min(cands)
        s = s[start:]
    return _parse_json_span(s)


def _parse_json_span(s: str):
    """Balance the first {...} or [...] span, tracking string/escape state."""
    s = s.lstrip()
    if not s:
        raise ValueError("empty span")
    open_ch = s[0]
    if open_ch == "{":
        close_ch = "}"
    elif open_ch == "[":
        close_ch = "]"
    else:
        return json.loads(s)  # best effort
    depth = 0
    end = -1
    in_str = False
    esc = False
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        return json.loads(s)
    return json.loads(s[: end + 1])


# ---------------------------------------------------------------------------
# Single-file atomic output (one lesson = one file)
# ---------------------------------------------------------------------------

def split_and_write(out_root: Path, cp_id: str, cefr: str, entity: str, obj: dict, config: dict) -> list[str]:
    """Write the generated entity as ONE file under out_root/<cefr>/<cp_id>/.
    file_split.mode is always single_file for this toolkit (requirement)."""
    cp_dir = out_root / cefr / cp_id
    cp_dir.mkdir(parents=True, exist_ok=True)
    fname = "lesson.json" if entity == "lesson" else ("duoradio.json" if entity == "duoradio_episode" else f"{slugify(cp_id)}.json")
    fp = cp_dir / fname
    write_json_atomic(fp, obj)
    rel_base = out_root.parent
    return [str(fp.relative_to(rel_base))]


# ---------------------------------------------------------------------------
# _post_process: force structural metadata + locked-target re-injection
# ---------------------------------------------------------------------------

def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip().lower()


def _authoritative_texts(lesson: dict) -> list[str]:
    """Collect authoritative field values across exercises (for lock check)."""
    texts: list[str] = []
    for ex in lesson.get("exercises") or []:
        if not isinstance(ex, dict):
            continue
        field = _TARGET_FIELD.get(ex.get("exercise_type"))
        if field and ex.get(field):
            texts.append(str(ex[field]))
        if ex.get("target_sentence"):
            texts.append(str(ex["target_sentence"]))
        if ex.get("answer"):
            texts.append(str(ex["answer"]))
    return texts


def _post_process(cp: dict, obj, config: dict) -> dict:
    """Normalize/lock the generated object. For a lesson:
      - force structural metadata from the content point (id/type/cefr/section_id/unit_id/title/curve_plan)
      - ensure locked vocab targets are in target_vocab
      - re-inject a locked SENTENCE target into the first translate-type exercise whose
        target_sentence is empty (best-effort; DL-Lock gate hard-verifies the rest)
    """
    if not isinstance(obj, dict):
        return obj
    entity = cp.get("entity", "lesson")
    cefr = (cp.get("cefr") or "").upper()
    seed = cp.get("seed") or {}

    if entity == "lesson":
        # force structural metadata
        obj["id"] = cp["id"]
        obj["type"] = "lesson"
        if cefr:
            obj["cefr"] = cefr
        for k in ("section_id", "unit_id"):
            if cp.get(k) is not None:
                obj[k] = cp[k]
        if seed.get("title") or cp.get("title"):
            obj["title"] = seed.get("title") or cp.get("title")
        curve = resolve_curve_plan(cp, config)
        if curve:
            obj["curve_plan"] = curve

        locked = seed.get("locked_targets") or cp.get("locked_targets") or []
        # vocab → target_vocab
        vocab = [t.get("text") for t in locked if t.get("kind") == "vocab" and t.get("text")]
        if vocab:
            tv = list(dict.fromkeys(obj.get("target_vocab") or []))
            for v in vocab:
                if v not in tv:
                    tv.append(v)
            obj["target_vocab"] = tv

        # sentence targets → best-effort fill empty target_sentence on a translate-type ex
        sentences = [t.get("text") for t in locked if t.get("kind") == "sentence" and t.get("text")]
        present = {_norm(t) for t in _authoritative_texts(obj)}
        unused = [s for s in sentences if _norm(s) not in present]
        for ex in obj.get("exercises") or []:
            if not unused:
                break
            if not isinstance(ex, dict):
                continue
            field = _TARGET_FIELD.get(ex.get("exercise_type"))
            if field and field == "target_sentence" and not (ex.get(field) or "").strip():
                ex[field] = unused.pop(0)
    elif entity == "duoradio_episode":
        obj["id"] = cp["id"]
        obj["type"] = "duoradio_episode"
        if cefr:
            obj["cefr"] = cefr
    return obj


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

def make_client(config: dict) -> AIBridge:
    llm = config["llm"]
    return AIBridge(provider=llm.get("provider", "claude_code"), model=llm.get("generate_model", "sonnet"))


def _max_tokens_for(cp: dict, config: dict) -> int:
    cefr = (cp.get("cefr") or "").upper()
    by_level = {str(k).upper(): v for k, v in (config.get("llm", {}).get("max_tokens_by_level") or {}).items()}
    if cefr in by_level:
        return int(by_level[cefr])
    return int(config.get("llm", {}).get("max_tokens", 4096))


def generate_one(cp: dict, client: AIBridge, config: dict, tk_root: Path) -> dict:
    """Generate one content point (a lesson or a duoradio episode); return meta."""
    llm = config["llm"]
    entity = cp.get("entity", "lesson")
    schema_path = tk_root / config["paths"]["schemas_dir"] / f"{entity}.json"
    schema_json = load_json(schema_path) if schema_path.exists() else {}
    prompts_dir = tk_root / config["paths"]["prompts_dir"]
    tmpl_name = cp.get("prompt_template", f"{entity}.md")
    prompt_version = _prompt_version(prompts_dir / tmpl_name)
    template = (prompts_dir / tmpl_name).read_text(encoding="utf-8")
    context = build_context(cp, schema_json, prompt_version, config)
    prompt = render_template(template, context)

    max_retries = int(llm.get("max_retries", 3))
    max_tokens = _max_tokens_for(cp, config)
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat(
                messages=prompt,
                system=(
                    "你是多邻国风格英语课程内容生成专家。严格按要求输出 JSON（无 markdown 代码块、无解释）。"
                    "内容必须事实正确、适龄、贴合指定 CEFR 等级与认知层级；不得编造；不得输出 xp/hearts/streak 等运行时数值。"
                ),
                temperature=float(llm.get("temperature", 0.7)),
                max_tokens=max_tokens,
            )
            obj = extract_json(resp.content)
            if isinstance(obj, list):  # bare array → wrap
                obj = {"exercises": obj} if entity == "lesson" else {"turns": obj}
            if not isinstance(obj, dict):
                raise ValueError("model output is not a JSON object")
            obj = _post_process(cp, obj, config)
            out_root = tk_root / config["paths"]["output_dir"]
            cefr = (cp.get("cefr") or config["product"].get("default_cefr", "A1")).upper()
            files = split_and_write(out_root, cp["id"], cefr, entity, obj, config)
            meta = {
                "content_point_id": cp["id"],
                "entity": entity,
                "cefr": cefr,
                "model_version": resp.model,
                "prompt_version": prompt_version,
                "files": files,
            }
            write_json_atomic(out_root / cefr / cp["id"] / "_meta.json", meta)
            return meta
        except (RateLimitError, NetworkError, ProviderError) as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(min(2 ** attempt, 16))
        except AuthenticationError:
            raise
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
    raise RuntimeError(f"failed after {max_retries} attempts: {last_err}")


def _prompt_version(path: Path) -> str:
    if not path.exists():
        return "v0"
    import hashlib
    h = hashlib.sha1(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()[:8]
    return f"sha1:{h}"


# ---------------------------------------------------------------------------
# Selection (resume + filters)
# ---------------------------------------------------------------------------

def select_items(content_list: list, state: dict, args) -> list:
    done = set(state.get("done", {}).keys())
    items = list(content_list)
    if args.only:
        wanted = set(args.only.split(","))
        items = [c for c in items if c.get("id") in wanted]
        return items
    if not args.force:
        items = [c for c in items if c.get("id") not in done]
    if args.sample:
        rng = random.Random(args.seed or 0)
        items = rng.sample(items, min(args.sample, len(items))) if items else []
    elif args.limit:
        items = items[: args.limit]
    return items


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="duolingo-english-data-gen toolkit generator")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--root", default=None, help="toolkit root dir (default: cwd)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--cefr", default=None, help="only this CEFR's content points (A1/A2/B1/B2)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tk_root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    config = load_json(tk_root / args.config)
    content_list = load_content_list(tk_root, config, args.cefr)
    state_file = tk_root / config["paths"]["state_file"]
    state = load_state(state_file)

    items = select_items(content_list, state, args)
    cefr_tag = f" [cefr={args.cefr}]" if args.cefr else ""
    print(f"[generate]{cefr_tag} {len(items)} content point(s) to generate "
          f"(done={len(state.get('done', {}))}, failed={len(state.get('failed', {}))}).")

    if args.dry_run or not items:
        for c in items:
            print(f"  - {c.get('id')}  [{c.get('entity')}/{c.get('cefr')}]")
        return 0

    client = make_client(config)

    for cp in items:
        cid = cp["id"]
        try:
            meta = generate_one(cp, client, config, tk_root)
            state.setdefault("done", {})[cid] = meta
            state.get("failed", {}).pop(cid, None)
            print(f"  ✓ {cid}")
        except AuthenticationError as e:
            print(f"[generate] auth error, stopping: {e}", file=sys.stderr)
            save_state(state_file, state)
            return 2
        except Exception as e:
            attempts = state.setdefault("failed", {}).get(cid, {}).get("attempts", 0) + 1
            state["failed"][cid] = {"attempts": attempts, "last_error": str(e)}
            print(f"  ✗ {cid}  ({e})")
        save_state(state_file, state)

    n_done = len(state.get("done", {}))
    n_failed = len(state.get("failed", {}))
    print(f"[generate] done={n_done} failed={n_failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
