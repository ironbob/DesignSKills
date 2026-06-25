#!/usr/bin/env python3
"""Validate the outline.json contract for book-talk-planner.

``outline.json`` 是唯一事实源（机器契约 / 下游 skill 交接物）；``outline.md`` 是它的渲染，
``validate_contract.py`` 对账。本门检查 outline.json 的**内部完整性与覆盖**：

  O-META    meta 必填 + 枚举（input_mode / selectability.verdict / form / viral_potential）
  O-ID      topics 是数组；id 唯一、匹配 T+数字（如 T01）
  O-FIELDS  每 topic 必填字段 + 区间（hook_directions 1-2 / key_points 3-5）
            + P1 标准版字段（title_directions 2-3 / cover_direction）
  O-ANGLE   每 topic.angle 存在于 angle-library.md
  O-COVERAGE distinct angle ≥ 3
  O-COUNT   topics 数 ∈ [3, 8]
  O-CRED    credibility 条目结构合法 + level 枚举；title_only 输入风险联动；
            含史实/数据/因果迹象却无 credibility → 警告
  O-BANNED  无 banned / placeholder 词

有 ERROR 失败或 WARNING 通过率 < 80% 时退出非 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

INPUT_MODES = {"title_only", "title_plus_summary", "full_text"}
VERDICTS = {"worth_telling", "marginal", "thin"}
FORMS = {"series", "single"}
VIRAL = {"high", "medium", "low"}
CRED_LEVELS = {"credible", "uncertain", "unverified"}
ID_RE = re.compile(r"^T\d+$")
ANGLE_HEAD = re.compile(r"^### ([a-z][a-z0-9-]*) · ")

# banned / placeholder（值里禁用）
BANNED_RE = re.compile(r"TBD|TODO|FIXME|待定|待补|占位|适当处理|后续再说|xxx", re.IGNORECASE)

# 史实/数据/因果迹象（启发式：命中却无 credibility → 警告）
CLAIM_HINT_RE = re.compile(r"\d{2,4}\s*年|万|亿|\d+\s*%|因为|导致|由于|从而|使得|引发|死于|占领")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.passed: list[str] = []

    def err(self, rule: str, msg: str) -> None:
        self.errors.append(f"🔴 [{rule}] {msg}")

    def warn(self, rule: str, msg: str) -> None:
        self.warns.append(f"🟡 [{rule}] {msg}")

    def ok(self, rule: str, msg: str = "") -> None:
        self.passed.append(f"✅ [{rule}]" + (f" {msg}" if msg else ""))

    def ok_or(self, rule: str, cond: bool, msg_ok: str, msg_err: str,
              warn: bool = False) -> None:
        if cond:
            self.ok(rule, msg_ok)
        elif warn:
            self.warn(rule, msg_err)
        else:
            self.err(rule, msg_err)


def _nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _str_list(x: Any) -> list:
    return x if isinstance(x, list) else []


def load_angle_ids(lib_path: Path) -> set[str]:
    ids: set[str] = set()
    if not lib_path.exists():
        return ids
    in_fence = False
    for line in lib_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = ANGLE_HEAD.match(s)
        if m:
            ids.add(m.group(1))
    return ids


def scan_banned(obj: Any, path: str, r: Report) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            scan_banned(v, f"{path}.{k}", r)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            scan_banned(v, f"{path}[{i}]", r)
    elif isinstance(obj, str):
        hits = BANNED_RE.findall(obj)
        if hits:
            r.err("O-BANNED", f"{path}: banned/placeholder 命中 {hits}: {obj.strip()}")


def validate(data: Any, angle_ids: set[str]) -> Report:
    r = Report()

    if not isinstance(data, dict):
        r.err("O-META", "顶层不是 JSON 对象")
        return r

    # ---- O-BANNED 全局扫 ----
    before = len(r.errors)
    scan_banned(data, "$", r)
    if len(r.errors) == before:
        r.ok("O-BANNED", "无 banned/placeholder")

    # ---- O-META ----
    meta = data.get("meta")
    if not isinstance(meta, dict):
        r.err("O-META", "缺 meta 对象")
        meta = {}
    r.ok_or("O-META", _nonempty_str(meta.get("book")), "meta.book 有", "缺 meta.book")
    im = meta.get("input_mode")
    r.ok_or("O-META", im in INPUT_MODES, f"input_mode={im}", f"input_mode 非法 {im!r}（须 title_only/title_plus_summary/full_text）")
    r.ok_or("O-META", _nonempty_str(meta.get("user_angle_direction")), "user_angle_direction 有", "缺 meta.user_angle_direction")
    r.ok_or("O-META", _nonempty_str(meta.get("tone")), "tone 有", "缺 meta.tone")

    sel = meta.get("selectability")
    if not isinstance(sel, dict):
        r.err("O-META", "缺 meta.selectability 对象")
        sel = {}
    r.ok_or("O-META", sel.get("verdict") in VERDICTS, f"verdict={sel.get('verdict')}", f"selectability.verdict 非法 {sel.get('verdict')!r}")
    r.ok_or("O-META", sel.get("form") in FORMS, f"form={sel.get('form')}", f"selectability.form 非法 {sel.get('form')!r}")
    r.ok_or("O-META", sel.get("viral_potential") in VIRAL, f"viral_potential={sel.get('viral_potential')}", f"selectability.viral_potential 非法 {sel.get('viral_potential')!r}")
    r.ok_or("O-META", isinstance(sel.get("talkable_points_estimate"), int), "talkable_points_estimate 为 int", "selectability.talkable_points_estimate 须为 int")
    r.ok_or("O-META", _nonempty_str(sel.get("viral_reason")), "viral_reason 有", "缺 selectability.viral_reason")

    # ---- O-ID / O-COUNT ----
    topics = data.get("topics")
    if not isinstance(topics, list) or not topics:
        r.err("O-COUNT", "topics 须为非空数组")
        topics = []
    else:
        n = len(topics)
        r.ok_or("O-COUNT", 3 <= n <= 8, f"topics {n} 个（∈[3,8]）",
                f"topics {n} 个，超出 [3,8]（选题粒度失控）", warn=(n == 0))
        if not (3 <= n <= 8) and n > 0:
            r.err("O-COUNT", f"topics 数 {n} 不在 [3,8]")

    ids: list[str] = []
    angles_used: list[str] = []
    for i, t in enumerate(topics):
        if not isinstance(t, dict):
            r.err("O-FIELDS", f"topics[{i}] 不是对象")
            continue
        ctx = f"topics[{i}] ({t.get('id', '?')})"
        tid = t.get("id")
        r.ok_or("O-ID", isinstance(tid, str) and bool(ID_RE.match(tid or "")),
                f"{tid}: id 合法", f"{ctx}: id 非法 {tid!r}（须 T\\d+，如 T01）")
        if isinstance(tid, str):
            if tid in ids:
                r.err("O-ID", f"{ctx}: id 重复（{tid}）")
            ids.append(tid)

        # 必填标量
        r.ok_or("O-FIELDS", _nonempty_str(t.get("title")), f"{tid}: title 有", f"{ctx}: 缺 title")
        r.ok_or("O-FIELDS", _nonempty_str(t.get("angle_name")), f"{tid}: angle_name 有", f"{ctx}: 缺 angle_name")
        r.ok_or("O-FIELDS", _nonempty_str(t.get("golden_line_direction")), f"{tid}: golden_line_direction 有", f"{ctx}: 缺 golden_line_direction")
        r.ok_or("O-FIELDS", t.get("video_form") in FORMS, f"{tid}: video_form={t.get('video_form')}", f"{ctx}: video_form 非法 {t.get('video_form')!r}")
        r.ok_or("O-FIELDS", _nonempty_str(t.get("why_worth_telling")), f"{tid}: why_worth_telling 有", f"{ctx}: 缺 why_worth_telling")

        # angle ∈ library
        ang = t.get("angle")
        r.ok_or("O-ANGLE", isinstance(ang, str) and ang in angle_ids,
                f"{tid}: angle={ang} 在库",
                f"{ctx}: angle={ang!r} 不在 angle-library（可用：{sorted(angle_ids) or '加载失败'}）")
        if isinstance(ang, str):
            angles_used.append(ang)

        # 区间字段
        hooks = _str_list(t.get("hook_directions"))
        r.ok_or("O-FIELDS", 1 <= len(hooks) <= 2 and all(_nonempty_str(h) for h in hooks),
                f"{tid}: hook_directions {len(hooks)} 条", f"{ctx}: hook_directions 须 1-2 条非空串（现 {len(hooks)}）")
        kps = _str_list(t.get("key_points"))
        r.ok_or("O-FIELDS", 3 <= len(kps) <= 5 and all(_nonempty_str(k) for k in kps),
                f"{tid}: key_points {len(kps)} 条", f"{ctx}: key_points 须 3-5 条非空串（现 {len(kps)}）")

        # P1 标准版字段
        tds = _str_list(t.get("title_directions"))
        r.ok_or("O-FIELDS", 2 <= len(tds) <= 3 and all(_nonempty_str(x) for x in tds),
                f"{tid}: title_directions {len(tds)} 条", f"{ctx}: title_directions 须 2-3 条非空串（现 {len(tds)}）")
        r.ok_or("O-FIELDS", _nonempty_str(t.get("cover_direction")), f"{tid}: cover_direction 有", f"{ctx}: 缺 cover_direction")

        # ---- O-CRED credibility ----
        cred = t.get("credibility")
        if cred is None:
            cred = []
        if not isinstance(cred, list):
            r.err("O-CRED", f"{ctx}: credibility 须为数组")
            cred = []
        for j, c in enumerate(cred):
            if not isinstance(c, dict):
                r.err("O-CRED", f"{ctx}.credibility[{j}] 不是对象")
                continue
            r.ok_or("O-CRED", _nonempty_str(c.get("claim")), f"{tid}.cred[{j}]: claim 有", f"{ctx}.credibility[{j}]: 缺 claim")
            r.ok_or("O-CRED", c.get("level") in CRED_LEVELS, f"{tid}.cred[{j}]: level={c.get('level')}", f"{ctx}.credibility[{j}]: level 非法 {c.get('level')!r}（须 credible/uncertain/unverified）")
            r.ok_or("O-CRED", _nonempty_str(c.get("reason")), f"{tid}.cred[{j}]: reason 有", f"{ctx}.credibility[{j}]: 缺 reason")
        # 含史实/数据/因果迹象却无 credibility → 警告
        blob = " ".join([*_str_list(t.get("key_points")), *_str_list(t.get("hook_directions"))])
        if not cred and CLAIM_HINT_RE.search(blob):
            r.warn("O-CRED", f"{ctx}: key_points/hook 含史实/数据/因果迹象却无 credibility 标注（建议补）")

    # ---- O-COVERAGE ----
    distinct = set(angles_used)
    r.ok_or("O-COVERAGE", len(distinct) >= 3,
            f"distinct angle {len(distinct)} 个（≥3）",
            f"distinct angle 仅 {len(distinct)} 个 < 3（视角过于集中）")

    # ---- O-CRED 输入风险联动（title_only 应更保守） ----
    all_cred = [c for t in topics if isinstance(t, dict) for c in _str_list(t.get("credibility")) if isinstance(c, dict)]
    if im == "title_only" and all_cred:
        risky = sum(1 for c in all_cred if c.get("level") in {"unverified", "uncertain"})
        ratio = risky / len(all_cred)
        r.ok_or("O-CRED", ratio >= 0.5,
                f"title_only 输入：存疑/待核实占比 {ratio:.0%}（≥50%，保守）",
                f"title_only 输入：存疑/待核实占比仅 {ratio:.0%}（凭记忆应更保守，建议 ≥50%）",
                warn=True)

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a book-talk-planner outline.json")
    ap.add_argument("doc", type=Path, help="Path to outline.json")
    ap.add_argument("--lib", type=Path, default=None,
                    help="angle-library.md 路径（默认取本 skill 自带）")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.doc.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.doc}: JSON 解析失败：{exc}\n")
        return 2

    lib = args.lib or (Path(__file__).resolve().parent.parent / "references" / "angle-library.md")
    angle_ids = load_angle_ids(lib)
    if not angle_ids:
        print(f"⚠️  未从 {lib} 加载到视角 id（angle-library.md 是否在？）")

    r = validate(data, angle_ids)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_outline: {args.doc} ===")
    for line in r.errors + r.warns + r.passed:
        print(line)
    print(f"\nERROR: {len(r.errors)}  WARNING: {len(r.warns)}  PASSED: {len(r.passed)}")
    print(f"WARNING 通过率: {wp * 100:.0f}%  质量分: {quality * 100:.0f}%")

    if r.errors or wp < 0.80:
        print("\n结果：不合格（有 ERROR 或 WARNING 通过率 <80%）")
        return 1
    print("\n结果：合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
