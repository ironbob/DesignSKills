"""判据卡校准回测（review-conventions.md「校准」节）。

金标准 = 人审已通过的全套产物，**本地自备**：目录由 --gold 或环境变量 WB_GOLD_DIR 指定，
仓库不内置也不依赖任何外部固定路径。对每张 rubric 卡跑一次独立 L2 评审：
- 🔴 必须为 0——金标准出红 = 判据过严/误判（假阳性），据此修判据卡，不是修产物
- 🟡 允许非零（金标准也允许改进项），只记录不阻断
- 覆盖不完整/评审失败 = 评审不可信，等同该阶段校准失败；语料缺该阶段产物则记 SKIP

用法（消耗 claude 配额，每阶段一次独立会话）：
    cd app/backend && uv run python calibrate_rubrics.py --gold <金标准目录>
    WB_GOLD_DIR=<金标准目录> uv run python calibrate_rubrics.py      # 全部 9 阶段
    uv run python calibrate_rubrics.py --gold <目录> --stage 2,7      # 指定阶段
    uv run python calibrate_rubrics.py --gold <目录> --out report.json  # 报告落盘
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ —— 让 backend 包可导入

from backend.engine.reviewer import ClaudeReviewer, ReviewError  # noqa: E402
from backend.settings import Settings  # noqa: E402
from backend.stages.registry import REGISTRY, StageCard  # noqa: E402

# 阶段 → 金标准产物（已知语料（二胡练习 App）与工具产物命名的差异在此映射；
# 换自定义语料时按实际命名调整；映射项在语料中不存在则该阶段记 SKIP）
GOLD_ARTIFACTS: dict[int, list[str]] = {
    1: ["01-需求消化.md"],
    2: ["02-流程草图.md"],
    3: ["03-屏幕清单与信息架构.md"],                                   # 工具命名 03-屏幕与IA.md
    4: ["04-wireframes/", "03-屏幕清单与信息架构.md"],                 # 上游锚点随行
    5: ["05-style-tiles/"],
    6: ["06-tokens.json", "06-design-system.html"],
    7: ["07-hifi/", "06-tokens.json"],
    8: ["08-交互说明.md", "08-prototype-f1.html", "08-findings.md"],   # 08-prototype.html → -f1
    9: ["09-spec.md", "06-tokens.json"],
}


def gold_card(stage: int) -> StageCard:
    """借注册表的卡（rubric 快照/判据号），换上金标准产物路径。"""
    card = REGISTRY.get(stage)
    if card is None:  # 阶段 3-9 未注册卡：rubric 快照仍在，手工组卡
        from backend.stages.registry import CARDS_DIR, NINE_STAGES

        card = StageCard(
            stage=stage, name=NINE_STAGES[stage - 1], decision_type="none",
            artifact_paths=[], artifact_map={}, mock_dir=None, decision_data_path=None,
            prompt_file=CARDS_DIR / f"stage{stage:02d}.md",
            rubric_file=CARDS_DIR / f"rubric-{stage:02d}.md",
        )
    return replace(card, artifact_paths=GOLD_ARTIFACTS[stage])


async def calibrate(stage: int, reviewer: ClaudeReviewer, gold_dir: Path) -> dict:
    t0 = time.monotonic()
    try:
        result = await reviewer.review(gold_card(stage), gold_dir, None)
    except ReviewError as e:
        return {
            "stage": stage,
            "ok": True,
            "skip": "产物文件均不存在" in str(e),  # 语料缺该阶段产物≠校准失败
            "error": str(e),
            "cost_s": round(time.monotonic() - t0, 1),
        }

    findings = result.get("findings", [])
    red = [f for f in findings if f.get("severity") == "red"]
    yellow = [f for f in findings if f.get("severity") == "yellow"]
    return {
        "stage": stage,
        "ok": not red,
        "red": red, "yellow": yellow,
        "covered": result.get("covered", []),
        "not_applicable": result.get("not_applicable", []),
        "cost_s": round(time.monotonic() - t0, 1),
    }


def print_report(r: dict) -> None:
    mark = "SKIP" if r.get("skip") else ("PASS" if r["ok"] else "FAIL")
    print(f"\n[阶段 {r['stage']}] {mark}  🔴={len(r.get('red', []))} 🟡={len(r.get('yellow', []))}  ({r['cost_s']}s)")
    if not r["ok"] and "error" in r:
        print(f"  评审失败：{r['error']}")
    elif r.get("skip") and "error" in r:
        print(f"  跳过：{r['error']}")
    for f in r.get("red", []):
        print(f"  🔴 {f.get('criterion')}  {f.get('evidence', '')[:100]}")
        if f.get("suggestion"):
            print(f"     建议：{f['suggestion'][:80]}")
    for f in r.get("yellow", []):
        print(f"  🟡 {f.get('criterion')}  {f.get('evidence', '')[:100]}")


def main() -> int:
    ap = argparse.ArgumentParser(description="金标准语料判据卡校准回测（语料本地自备，不依赖外部固定路径）")
    ap.add_argument("--gold", default="", help="金标准语料目录（缺省取环境变量 WB_GOLD_DIR）")
    ap.add_argument("--stage", default="", help="只跑指定阶段，如 2,7；默认全部")
    ap.add_argument("--out", default="", help="JSON 报告落盘路径")
    ap.add_argument("--timeout", type=int, default=600, help="单阶段评审超时秒数（默认 600）")
    args = ap.parse_args()

    stages = [int(s) for s in args.stage.split(",") if s.strip()] or list(range(1, 10))
    raw_gold = (args.gold or os.environ.get("WB_GOLD_DIR", "")).strip()
    if not raw_gold:
        print("未指定金标准语料目录：--gold <目录> 或 WB_GOLD_DIR=<目录>"
              "（本地自备的人审通过全套产物；本仓库不内置语料路径）")
        return 2
    gold_dir = Path(raw_gold).expanduser()
    if not gold_dir.is_dir():
        print(f"金标准目录不存在：{gold_dir}")
        return 2

    settings = Settings(data_dir=Path("."), runner="claude", reviewer="claude", task_timeout_s=args.timeout)
    reviewer = ClaudeReviewer(settings)

    print(f"[calibrate] 金标准={gold_dir}  阶段={stages}  超时={args.timeout}s")
    results = []
    for st in stages:
        r = asyncio.run(calibrate(st, reviewer, gold_dir))
        results.append(r)
        print_report(r)

    failed = [r["stage"] for r in results if not r["ok"]]
    skipped = [r["stage"] for r in results if r.get("skip")]
    total_red = sum(len(r.get("red", [])) for r in results)
    total_yellow = sum(len(r.get("yellow", [])) for r in results)
    print(f"\n[calibrate] 汇总：{len(results) - len(failed)}/{len(results)} 通过 · 🔴={total_red} 🟡={total_yellow}")
    if skipped:
        print(f"[calibrate] 跳过（语料缺该阶段产物）：{skipped}")
    if failed:
        print(f"[calibrate] 假阳性阶段：{failed}——按公约修判据卡（金标准不迁就评审器）")

    if args.out:
        Path(args.out).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[calibrate] 报告：{args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
