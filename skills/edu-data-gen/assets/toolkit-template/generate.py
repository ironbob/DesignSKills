#!/usr/bin/env python3
"""Data-generation engine for an edu-data-gen toolkit.

Resumable / retrying / idempotent generator that calls the LLM via
ai_bridge (provider `claude_code` → ClaudeCodeDirectProvider) and writes
**multiple files per content point**.

Capabilities (hard requirements from the skill spec):
  - 中断/恢复 (interrupt/resume): progress persisted to state/state.json; reruns skip done items.
  - 重试 (retry): per-item retries up to config.llm.max_retries on LLM/parse error.
  - 幂等 (idempotent): done items are skipped unless --force.
  - 每内容点多文件 (multi-file): output split per config.file_split.by_field_group.

Usage:
  python generate.py                       # generate all pending content points (all grades)
  python generate.py --grade g5           # only one grade's content points
  python generate.py --limit 20           # only next 20 pending (sample-friendly)
  python generate.py --sample 20          # random sample of 20 pending
  python generate.py --only id1,id2       # specific ids (implies --force for those)
  python generate.py --target-bloom apply # only items whose target bloom == apply
  python generate.py --force              # regenerate even done items
  python generate.py --dry-run            # plan only, no LLM calls

Exits non-zero only on auth/config errors; per-item failures go to state.failed (resumable).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import traceback
from pathlib import Path


# ---------------------------------------------------------------------------
# Locate ai_bridge: walk up from this script to find a dir containing ai_bridge/.
# Toolkits live inside the DesignSkills repo, so ai_bridge is reachable upward.
# Override with env EDU_DATA_GEN_ROOT or PYTHONPATH if relocated.
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
    "analyze": "分析(拆解/比较)",
    "evaluate": "评价(判断/辩护)",
    "create": "创造(设计/组合)",
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


def load_content_list(tk_root: Path, config: dict, grade: str | None = None) -> list:
    """Load content points from config.paths.content_list.

    content_list is a per-grade directory (content_list/g3.json, g5.json, …).
    Legacy single-file form still supported. Files ending in .example.json are
    skipped (template demos). With --grade, only that grade's file/items load.
    """
    cl = tk_root / config["paths"]["content_list"]
    items: list = []
    if cl.is_dir():
        files = sorted(f for f in cl.glob("*.json") if not f.name.endswith(".example.json"))
        if grade:
            files = [f for f in files if f.stem == grade]  # per-grade file named <grade>.json
        for f in files:
            data = load_json(f)
            if isinstance(data, list):
                items.extend(data)
    elif cl.is_file():
        items = load_json(cl)
    else:
        raise FileNotFoundError(f"content_list not found: {cl}")
    if grade:
        items = [c for c in items if c.get("grade") == grade]  # belt-and-suspenders
    return items


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------

def slugify(content_point_id: str) -> str:
    # <entity>-<subject>-<grade>-<slug...> → last segment(s); fall back to id tail.
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


def build_context(cp: dict, schema_json, prompt_version: str, config: dict) -> dict:
    grade = cp.get("grade", config["product"].get("default_grade", "g5"))
    bloom = cp.get("bloom", "understand")
    ctx = {
        "entity": cp.get("entity", ""),
        "grade": grade,
        "bloom": bloom,
        "bloom_label": BLOOM_LABELS.get(bloom, bloom),
        "id": cp.get("id", ""),
        "knowledge_point_refs": cp.get("knowledge_point_refs", []),
        "seed": cp.get("seed", {}),
        "seed_json": cp.get("seed", {}),
        "schema_json": schema_json or {},
        "product_name": config["product"].get("name", ""),
        "subject": config["product"].get("subject", ""),
        "prompt_version": prompt_version,
    }
    # flatten seed.* so {{seed.term}} works too
    for k, v in (cp.get("seed") or {}).items():
        ctx.setdefault(f"seed.{k}", v)
    return ctx


# ---------------------------------------------------------------------------
# JSON extraction from LLM output
# ---------------------------------------------------------------------------

def extract_json(text: str):
    """Strip code fences / surrounding prose and parse the first JSON object."""
    if text is None:
        raise ValueError("empty model output")
    s = text.strip()
    # strip ```json ... ``` / ``` ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", s, re.S)
    if fence:
        s = fence.group(1)
    else:
        # find first {...} balanced-ish span
        start = s.find("{")
        if start == -1:
            raise ValueError("no JSON object found in model output")
        s = s[start:]
    # trim trailing non-json after the matching brace (best effort)
    return _parse_json_obj(s)


def _parse_json_obj(s: str):
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
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end == -1:
        # fall back to whole thing
        return json.loads(s)
    return json.loads(s[: end + 1])


# ---------------------------------------------------------------------------
# Multi-file split
# ---------------------------------------------------------------------------

def split_and_write(out_root: Path, cp_id: str, grade: str, entity: str, obj: dict, config: dict) -> list[str]:
    """Write the generated FLAT entity object as one or more files under
    out_root/<grade>/<cp_id>/.

    file_split.by_field_group[entity] may be either:
      - dict: {group_name: [field, ...]}  → partition flat fields into multiple files
      - list: [group_name, ...]           → treat each group_name as a top-level key
    Either way validate.py merges the files back into the flat entity for gating.
    """
    cp_dir = out_root / grade / cp_id
    cp_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(cp_id)
    written: list[str] = []
    fs = config.get("file_split", {})
    mode = fs.get("mode", "by_field_group")
    rel_base = out_root.parent  # so paths read "output/<grade>/<id>/<file>"

    def _rel(fp: Path) -> str:
        return str(fp.relative_to(rel_base))

    if mode == "single_file":
        fp = cp_dir / f"{slug}.json"
        write_json_atomic(fp, obj)
        written.append(_rel(fp))
        return written

    groups = fs.get("by_field_group", {}).get(entity)
    if not groups:  # no rule for this entity → single file
        fp = cp_dir / f"{slug}.json"
        write_json_atomic(fp, obj)
        written.append(_rel(fp))
        return written

    if isinstance(groups, dict):  # field-partition form (preferred)
        for g, fields in groups.items():
            piece = {f: obj[f] for f in fields if isinstance(obj, dict) and f in obj}
            fp = cp_dir / f"{slug}.{g}.json"
            write_json_atomic(fp, piece)
            written.append(_rel(fp))
    else:  # legacy list form: group names as top-level keys
        for g in groups:
            piece = obj.get(g) if isinstance(obj, dict) else None
            fp = cp_dir / f"{slug}.{g}.json"
            write_json_atomic(fp, piece if isinstance(piece, dict) else {})
            written.append(_rel(fp))
    return written


# ---------------------------------------------------------------------------
# Core generation
# ---------------------------------------------------------------------------

def make_client(config: dict) -> AIBridge:
    llm = config["llm"]
    return AIBridge(provider=llm.get("provider", "claude_code"), model=llm.get("generate_model", "sonnet"))


def generate_one(cp: dict, client: AIBridge, config: dict, tk_root: Path) -> dict:
    """Generate one content point; return provenance+files. Raises on hard failure."""
    llm = config["llm"]
    entity = cp.get("entity", "material")
    schema_path = tk_root / config["paths"]["schemas_dir"] / f"{entity}.json"
    schema_json = load_json(schema_path) if schema_path.exists() else {}
    prompt_version = _prompt_version(tk_root / config["paths"]["prompts_dir"] / cp.get("prompt_template", f"{entity}.md"))
    tmpl_path = tk_root / config["paths"]["prompts_dir"] / cp.get("prompt_template", f"{entity}.md")
    template = tmpl_path.read_text(encoding="utf-8")
    context = build_context(cp, schema_json, prompt_version, config)
    prompt = render_template(template, context)

    max_retries = int(llm.get("max_retries", 3))
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = client.chat(
                messages=prompt,
                system=(
                    "你是教育内容生成专家。严格按要求输出 JSON（无 markdown 代码块、无解释）。"
                    "内容必须事实正确、适龄、贴合指定年级与认知层级；不得编造。"
                ),
                temperature=float(llm.get("temperature", 0.7)),
                max_tokens=int(llm.get("max_tokens", 2048)),
            )
            obj = extract_json(resp.content)
            if not isinstance(obj, dict):
                raise ValueError("model output is not a JSON object")
            out_root = tk_root / config["paths"]["output_dir"]
            grade = cp.get("grade", config["product"].get("default_grade", "g5"))
            files = split_and_write(out_root, cp["id"], grade, entity, obj, config)
            # write _meta (provenance) — G8 traceability
            meta = {
                "content_point_id": cp["id"],
                "entity": entity,
                "grade": grade,
                "bloom": cp.get("bloom"),
                "model_version": resp.model,
                "prompt_version": prompt_version,
                "files": files,
            }
            write_json_atomic(out_root / grade / cp["id"] / "_meta.json", meta)
            return meta
        except (RateLimitError, NetworkError, ProviderError) as e:
            last_err = f"{type(e).__name__}: {e}"
            time.sleep(min(2 ** attempt, 16))  # backoff, respects 429
        except AuthenticationError:
            raise  # bubble up — not retryable
        except Exception as e:  # parse / schema / value errors
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
    if args.target_bloom:
        items = [c for c in items if c.get("bloom") == args.target_bloom]
    if args.only:
        wanted = set(args.only.split(","))
        items = [c for c in items if c.get("id") in wanted]
        return items  # --only implies regenerating those regardless of done
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
    ap = argparse.ArgumentParser(description="edu-data-gen toolkit generator")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--root", default=None, help="toolkit root dir (default: cwd)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sample", type=int, default=None)
    ap.add_argument("--only", default=None)
    ap.add_argument("--target-bloom", dest="target_bloom", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--grade", default=None, help="only this grade's content points (e.g. g5)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tk_root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    config = load_json(tk_root / args.config)
    content_list = load_content_list(tk_root, config, args.grade)
    state_file = tk_root / config["paths"]["state_file"]
    state = load_state(state_file)

    items = select_items(content_list, state, args)
    grade_tag = f" [grade={args.grade}]" if args.grade else ""
    print(f"[generate]{grade_tag} {len(items)} content point(s) to generate "
          f"(done={len(state.get('done', {}))}, failed={len(state.get('failed', {}))}).")

    if args.dry_run or not items:
        for c in items:
            print(f"  - {c.get('id')}  [{c.get('entity')}/{c.get('grade')}/{c.get('bloom')}]")
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
        # persist after each item → interrupt-safe
        save_state(state_file, state)

    n_done = len(state.get("done", {}))
    n_failed = len(state.get("failed", {}))
    print(f"[generate] done={n_done} failed={n_failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
