"""增量变更影响分析：结构校验（L1 gate 用）+ 确定性执行计划（planner）。

分工（防讨好/防幻觉）：
- AI 只产「影响分析」结构化事实：哪些页面增/改/删、级别、受影响流程/导航/状态、共享面；
- planner 由结构确定性算出 stages_to_rerun 与回归范围——程序可消费，不信任 AI 自报阶段；
- 校验器保证结构合法、页面存在性对得上基线盘点、导航/流程/共享变更必带回归页。

分级→阶段映射（SKILL.md「修改词汇四层级」+ 增量规则，逐条对齐）：
  content   → {7, 9}                    （仅页面规格/文案；状态有变 → 追加 8）
  component → {6, 7, 9}                 （更新设计系统后重出受影响页面）
  layout    → {4, 7} → 追加 8           （必须回阶段 4，并同步后续相关产物）
  style     → {6, 7, 9}                 （更新 token 后重出受影响页面）
  新增页面  → {2, 3, 4, 7} → 追加 8     （更新流程/IA/盘点 + 线框/高保真/交互/crit/规格）
  任何变更  → 9 恒在                     （最终规格自包含，不允许跳过）
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

LEVELS = ("content", "component", "layout", "style")

_LEVEL_STAGES: dict[str, set[int]] = {
    "content": {7},
    "component": {6, 7},
    "layout": {4, 7},
    "style": {6, 7},
}

_SCREEN_ROW = re.compile(r"^\|\s*(S\d+)\s*\|\s*([^|]+)", re.M)


def screen_rows(project_dir: Path) -> list[dict[str, str]]:
    """从 03-屏幕与IA.md 盘点表解析 (page_id, name)；页面注册表与影响分析共用的基线事实。"""
    f = project_dir / "03-屏幕与IA.md"
    if not f.exists():
        return []
    rows = _SCREEN_ROW.findall(f.read_text(encoding="utf-8"))
    return [{"page_id": pid, "name": name.strip() or pid} for pid, name in rows]


def load_impact(revision_dir: Path) -> dict[str, Any] | None:
    """读 00-impact.json（阶段 0 产物）；缺失/不可解析返回 None。"""
    f = revision_dir / "00-impact.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def validate_impact(analysis: dict[str, Any], baseline_pages: list[str]) -> list[str]:
    """结构校验（阶段 0 的 L1 gate 主体）。返回 problems 列表（空=过）。"""
    problems: list[str] = []
    pages = analysis.get("pages")
    if not isinstance(pages, dict):
        return ["pages 缺失或非对象（必须含 added/modified/removed 三组）"]
    for key in ("added", "modified", "removed"):
        if not isinstance(pages.get(key), list):
            problems.append(f"pages.{key} 缺失或非数组")
    if problems:
        return problems
    baseline = set(baseline_pages)
    seen: set[str] = set()
    for p in pages["added"]:
        pid = p.get("page_id") if isinstance(p, dict) else None
        if not pid:
            problems.append("added 存在缺 page_id 的条目")
        elif pid in baseline:
            problems.append(f"新增页 {pid} 已在基线盘点中（新增页不得与基线冲突）")
        elif pid in seen:
            problems.append(f"页面 {pid} 在影响分析中重复出现")
        seen.add(pid)
    for p in pages["modified"]:
        if not isinstance(p, dict) or not p.get("page_id"):
            problems.append("modified 存在缺 page_id 的条目")
            continue
        pid = p["page_id"]
        if pid not in baseline:
            problems.append(f"修改页 {pid} 不在基线盘点中（不能修改不存在的页面）")
        if p.get("level") not in LEVELS:
            problems.append(f"修改页 {pid} 级别非法（{'/'.join(LEVELS)}）：{p.get('level')}")
        if pid in seen:
            problems.append(f"页面 {pid} 在影响分析中重复出现")
        seen.add(pid)
    for p in pages["removed"]:
        pid = p.get("page_id") if isinstance(p, dict) else None
        if not pid:
            problems.append("removed 存在缺 page_id 的条目")
        elif pid not in baseline:
            problems.append(f"删除页 {pid} 不在基线盘点中")
        elif pid in seen:
            problems.append(f"页面 {pid} 在影响分析中重复出现")
        seen.add(pid)
    if not (pages["added"] or pages["modified"] or pages["removed"]):
        problems.append("影响分析无任何页面变更（无变更则不应创建 revision）")
    shared = analysis.get("shared_change") or {}
    cross_cutting = bool(analysis.get("navigation") or analysis.get("flows") or shared.get("tokens") or shared.get("components"))
    if cross_cutting and not (analysis.get("regression_pages") or []):
        problems.append("导航/流程/共享 token/组件受影响，但 regression_pages 为空（必须声明回归验证范围）")
    for r in analysis.get("regression_pages") or []:
        if r in seen:
            problems.append(f"回归页 {r} 同时出现在变更页中（变更页本身要重做，不属于回归验证）")
    if not analysis.get("summary"):
        problems.append("summary 缺失（一句话变更摘要）")
    return problems


def plan_from_impact(analysis: dict[str, Any]) -> dict[str, Any]:
    """确定性执行计划：由结构化分析算变更级别、重跑阶段、回归范围。

    输出（程序消费，confirm 锁进 revisions.impact.plan）：
      change_levels / stages_to_rerun / regression_pages / rationale
    """
    pages = analysis.get("pages") or {}
    added = [p["page_id"] for p in pages.get("added", []) if isinstance(p, dict) and p.get("page_id")]
    modified = [p for p in pages.get("modified", []) if isinstance(p, dict) and p.get("page_id")]
    removed = [p["page_id"] for p in pages.get("removed", []) if isinstance(p, dict) and p.get("page_id")]
    shared = analysis.get("shared_change") or {}
    states = bool(analysis.get("states"))

    levels: list[str] = []
    for p in modified:
        if p.get("level") in LEVELS and p["level"] not in levels:
            levels.append(p["level"])
    if shared.get("tokens") and "style" not in levels:
        levels.append("style")
    if shared.get("components") and "component" not in levels:
        levels.append("component")

    stages: set[int] = set()
    rationale: list[str] = []
    if added:
        stages |= {2, 3, 4, 7}
        rationale.append(f"新增页面 {added}：更新流程/IA/盘点，完成线框与高保真")
    for lvl in levels:
        stages |= _LEVEL_STAGES[lvl]
        rationale.append(f"{lvl} 级变更：{'/'.join(str(s) for s in sorted(_LEVEL_STAGES[lvl]))} 重跑")
    if added or "layout" in levels or states:
        stages |= {8}
        why = "新增页面/layout" if (added or "layout" in levels) else "状态变更"
        rationale.append(f"{why}：交互矩阵与 crit 必须重验（不允许为增量跳过 L2 crit）")
    stages |= {9}
    rationale.append("9 恒在：最终规格必须自包含（含基线与变更记录）")

    regression = [r for r in (analysis.get("regression_pages") or []) if r]
    return {
        "change_levels": levels,
        "pages": {"added": added, "modified": [p["page_id"] for p in modified], "removed": removed},
        "stages_to_rerun": sorted(stages),
        "regression_pages": sorted(set(regression)),
        "rationale": rationale,
    }
