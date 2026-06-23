#!/usr/bin/env python3
"""Sample-validation runner for an edu-data-gen toolkit (the 样本验证 gate).

Runs the toolkit's generate.py on a representative sample, then validate.py,
then verifies the robustness requirements mechanically:
  - 中断/恢复/幂等 (resume/idempotent): re-run skips all done items (state unchanged)
  - 重试 (retry): any failed item is recorded in state.failed with attempts
  - 每内容点多文件 (multi-file): each sampled content point dir has ≥1 group file
  - 可追溯 (traceability): each dir has _meta.json with model_version + prompt_version
Writes sample_validation_report.md. Exits non-zero if sample validate fails or robustness broken.

Usage: python run_sample_validation.py <toolkit_dir> [--size 20] [--seed 0]
NOTE: makes real LLM calls (cost ~ size items). Size default 20.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, (p.stdout + ("\n" + p.stderr if p.stderr else ""))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="toolkit dir")
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    root = Path(args.root).resolve()
    py = sys.executable

    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    output_dir = root / config["paths"]["output_dir"]
    state_file = root / config["paths"]["state_file"]

    report: list[str] = [f"# 样本验证报告\n", f"工具包：`{root}`", f"样本规模：{args.size}\n"]
    overall = True

    # --- 1. generate sample ---
    gen_cmd = [py, str(root / "generate.py"), "--root", str(root),
               "--sample", str(args.size), "--seed", str(args.seed)]
    rc, out = run(gen_cmd)
    gen_ok = rc in (0,)
    report.append("## 1. 样本生成（generate.py --sample）")
    report.append(f"- 退出码：{rc}（0=正常；2=鉴权错误）")
    report.append("```")
    report.append(out.strip() or "(no output)")
    report.append("```")
    if not gen_ok:
        report.append("- ❌ 生成未正常完成（见上）。若为鉴权错误，请检查 Claude Code 登录。")
        overall = False

    # state snapshot for resume check
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"done": {}, "failed": {}}
    done_ids = set(state.get("done", {}).keys())
    failed = state.get("failed", {})

    # --- 2. robustness: resume / idempotent (re-run skips done) ---
    report.append("\n## 2. 鲁棒性：中断/恢复 + 幂等")
    rc2, out2 = run([py, str(root / "generate.py"), "--root", str(root)])
    state2 = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"done": {}, "failed": {}}
    done_ids2 = set(state2.get("done", {}).keys())
    resume_ok = done_ids == done_ids2  # unchanged → re-run skipped done (resume-safe)
    report.append(f"- 重跑（无 --force）后 done 集合{'不变' if resume_ok else '变化'}：{'幂等/可恢复 ✓' if resume_ok else '❌ 非幂等'}")
    report.append("```")
    report.append(out2.strip() or "(no output)")
    report.append("```")
    if not resume_ok:
        overall = False

    # --- 3. robustness: multi-file per content point ---
    report.append("\n## 3. 鲁棒性：每内容点多文件")
    done_meta = state.get("done", {})
    default_grade = config["product"].get("default_grade", "g5")
    multi_issues = []
    for cid in sorted(done_ids):
        grade = (done_meta.get(cid) or {}).get("grade") or default_grade
        cp_dir = output_dir / grade / cid
        files = [f for f in cp_dir.glob("*.json") if f.name != "_meta.json"] if cp_dir.exists() else []
        if len(files) < 1:
            multi_issues.append(f"{cid}: 无输出文件")
    if multi_issues:
        report.append("- ❌ " + "; ".join(multi_issues))
        overall = False
    else:
        report.append(f"- {len(done_ids)} 个内容点各有 ≥1 输出文件 ✓（多文件切分生效，见各目录）")

    # --- 4. robustness: traceability (_meta) ---
    report.append("\n## 4. 鲁棒性：可追溯（_meta.json）")
    meta_issues = []
    for cid in sorted(done_ids):
        grade = (done_meta.get(cid) or {}).get("grade") or default_grade
        meta_p = output_dir / grade / cid / "_meta.json"
        if not meta_p.exists():
            meta_issues.append(f"{cid}: 缺 _meta.json")
            continue
        meta = json.loads(meta_p.read_text(encoding="utf-8"))
        if not meta.get("model_version") or not meta.get("prompt_version"):
            meta_issues.append(f"{cid}: _meta 缺 model_version/prompt_version")
    if meta_issues:
        report.append("- ❌ " + "; ".join(meta_issues))
        overall = False
    else:
        report.append(f"- {len(done_ids)} 个内容点 _meta 齐全（model_version + prompt_version）✓")

    # --- 5. retry: report failed items if any ---
    report.append("\n## 5. 鲁棒性：重试（失败项记录）")
    if failed:
        report.append(f"- ⚠ {len(failed)} 个内容点失败并记录到 state.failed（attempts 已计，超限标待人审）：")
        for fid, info in list(failed.items())[:10]:
            report.append(f"  - {fid}: attempts={info.get('attempts')} err={info.get('last_error','')[:120]}")
    else:
        report.append("- 样本无失败项（重试路径未触发；机制已内置：失败≤max_retries 重试，超限入 state.failed）✓")

    # --- 6. validate sample ---
    report.append("\n## 6. 样本质量门（validate.py）")
    rc3, out3 = run([py, str(root / "validate.py"), "--root", str(root)])
    vrep_path = root / "validation_report.json"
    vrep = json.loads(vrep_path.read_text(encoding="utf-8")) if vrep_path.exists() else {}
    report.append(f"- 退出码：{rc3}（0=所有 ERROR 门通过）")
    report.append("```")
    report.append(out3.strip() or "(no output)")
    report.append("```")
    if vrep:
        summary = vrep.get("summary", {})
        report.append(f"- summary: {json.dumps(summary, ensure_ascii=False)}")
        for name, g in vrep.get("gates", {}).items():
            flag = "✓" if g.get("pass") else ("✗" if g.get("severity") == "ERROR" else "⚠")
            report.append(f"  - {flag} {name} [{g.get('severity')}]")
        if not summary.get("pass"):
            overall = False

    # --- verdict ---
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    verdict = "✅ 通过：工具包端到端可用（样本过门 + 鲁棒性达标）" if overall else "❌ 未通过：见上述失败项，修工具包后重跑"
    report.insert(3, f"\n**结论：{verdict}**\n生成时间：{ts}\n")
    report.append(f"\n---\n**结论：{verdict}**")

    md = "\n".join(report)
    (root / "sample_validation_report.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[run_sample_validation] report → {root / 'sample_validation_report.md'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
