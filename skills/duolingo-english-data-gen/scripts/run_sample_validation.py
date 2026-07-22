#!/usr/bin/env python3
"""Sample-validation runner for a duolingo-english-data-gen toolkit (样本验证).

Runs the toolkit end-to-end on a representative sample and proves robustness:
  - generate.py (one LLM call per lesson → ordered exercise array)
  - generate_audio.py (TTS for every spoken string; audio_ref inlined)
  - validate.py (G1/G2/G5-G8 + DL-* gates)
  - robustness: 中断/恢复/幂等, 单文件原子课, 可追溯, 曲线合规(末题 end_on_easy), 目标句锁定
Writes sample_validation_report.md. Exits non-zero on failure.
Usage: python run_sample_validation.py <toolkit_dir> [--size 3] [--seed 0] [--skip-audio]
NOTE: makes real LLM calls (cost ~ size lessons). Set DUOLINGO_TTS_ROOT if toolkit is not
inside the repo that holds tts_providers.py.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd: list[str], env=None) -> tuple[int, str]:
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return p.returncode, (p.stdout + ("\n" + p.stderr if p.stderr else ""))


def cp_output_dir(output_dir: Path, cp: dict) -> Path:
    cefr = (cp.get("cefr") or "").upper() or "A1"
    return output_dir / cefr / cp["id"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="toolkit dir")
    ap.add_argument("--size", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-audio", action="store_true", help="skip generate_audio pass")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    py = sys.executable

    config = json.loads((root / "config.json").read_text(encoding="utf-8"))
    output_dir = root / config["paths"]["output_dir"]
    state_file = root / config["paths"]["state_file"]
    default_cefr = config["product"].get("default_cefr", "A1")

    report: list[str] = [f"# 样本验证报告\n", f"工具包：`{root}`", f"样本规模：{args.size}（CEFR 默认 {default_cefr}）\n"]
    overall = True

    # --- 1. generate sample ---
    gen_cmd = [py, str(root / "generate.py"), "--root", str(root),
               "--cefr", default_cefr, "--sample", str(args.size), "--seed", str(args.seed)]
    rc, out = run(gen_cmd)
    report.append("## 1. 样本生成（generate.py --cefr --sample）")
    report.append(f"- 退出码：{rc}（0=正常；2=鉴权错误）")
    report.append("```")
    report.append(out.strip() or "(no output)")
    report.append("```")
    if rc not in (0,):
        report.append("- ❌ 生成未正常完成（若为鉴权错误，请检查 Claude Code 登录）。")
        overall = False

    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"done": {}, "failed": {}}
    done_ids = set(state.get("done", {}).keys())
    failed = state.get("failed", {})

    # --- 2. resume / idempotent ---
    report.append("\n## 2. 鲁棒性：中断/恢复 + 幂等")
    # Re-select only the completed sample without --force. This proves skipping done
    # items without accidentally generating the rest of the CEFR.
    only_done = ",".join(sorted(done_ids))
    resume_cmd = [py, str(root / "generate.py"), "--root", str(root),
                  "--cefr", default_cefr, "--only", only_done]
    rc2, out2 = run(resume_cmd) if only_done else (1, "no completed sample ids")
    state2 = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"done": {}, "failed": {}}
    resume_ok = done_ids == set(state2.get("done", {}).keys())
    report.append(f"- 重跑（无 --force）后 done 集合{'不变' if resume_ok else '变化'}：{'幂等/可恢复 ✓' if resume_ok else '❌ 非幂等'}")
    report.append("```")
    report.append(out2.strip() or "(no output)")
    report.append("```")
    if not resume_ok:
        overall = False

    # --- 3. single-file atomic lesson ---
    report.append("\n## 3. 鲁棒性：单文件原子课")
    done_meta = state.get("done", {})
    single_issues = []
    lesson_files = {}
    for cid in sorted(done_ids):
        cp = {"id": cid, "cefr": (done_meta.get(cid) or {}).get("cefr", default_cefr)}
        d = cp_output_dir(output_dir, cp)
        files = [f for f in d.glob("*.json") if f.name != "_meta.json"] if d.exists() else []
        if len(files) != 1:
            single_issues.append(f"{cid}: 期望 1 个内容 JSON，实际 {len(files)} 个")
        else:
            lesson_files[cid] = d / files[0]
    if single_issues:
        report.append("- ❌ " + "; ".join(single_issues))
        overall = False
    else:
        report.append(f"- {len(done_ids)} 节课各有 1 个 lesson.json + _meta.json ✓（单文件原子课）")

    # --- 4. traceability ---
    report.append("\n## 4. 鲁棒性：可追溯（_meta.json）")
    meta_issues = []
    for cid in sorted(done_ids):
        cp = {"id": cid, "cefr": (done_meta.get(cid) or {}).get("cefr", default_cefr)}
        meta_p = cp_output_dir(output_dir, cp) / "_meta.json"
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
        report.append(f"- {len(done_ids)} 节课 _meta 齐全 ✓")

    # --- 5. retry ---
    report.append("\n## 5. 鲁棒性：重试（失败项记录）")
    if failed:
        report.append(f"- ⚠ {len(failed)} 节失败并记录到 state.failed：")
        for fid, info in list(failed.items())[:10]:
            report.append(f"  - {fid}: attempts={info.get('attempts')} err={info.get('last_error','')[:120]}")
    else:
        report.append("- 样本无失败项 ✓")

    # --- 6. curve + lock proof (mechanical) ---
    report.append("\n## 6. 曲线合规 + 目标句锁定（机械抽查）")
    curve_issues = []
    for cid, lf in lesson_files.items():
        try:
            lesson = json.loads(lf.read_text(encoding="utf-8"))
        except Exception as e:
            curve_issues.append(f"{cid}: 读 lesson 失败 {e}")
            continue
        exs = lesson.get("exercises") or []
        if not exs:
            curve_issues.append(f"{cid}: 无 exercises")
            continue
        if exs[-1].get("stage") != "end_on_easy":
            curve_issues.append(f"{cid}: 末题 stage={exs[-1].get('stage')} ≠ end_on_easy")
    if curve_issues:
        report.append("- ❌ " + "; ".join(curve_issues))
        overall = False
    else:
        report.append(f"- {len(lesson_files)} 节课末题均为 end_on_easy ✓（曲线收尾合规）")

    # --- 7. audio pass ---
    if not args.skip_audio and (root / "generate_audio.py").exists():
        report.append("\n## 7. 音频生成（generate_audio.py）")
        env = None
        tts_root = __import__("os").environ.get("DUOLINGO_TTS_ROOT")
        if tts_root:
            report.append(f"- DUOLINGO_TTS_ROOT={tts_root}")
        rc4, out4 = run([py, str(root / "generate_audio.py"), "--root", str(root),
                         "--cefr", default_cefr, "--sample", str(args.size), "--seed", str(args.seed)])
        report.append(f"- 退出码：{rc4}")
        report.append("```")
        report.append(out4.strip() or "(no output)")
        report.append("```")
        if rc4 not in (0,):
            report.append("- ❌ 音频生成未成功（可能是 tts_providers 未找到——设 DUOLINGO_TTS_ROOT 指向含 tts_providers.py 的目录）。")
            overall = False
    else:
        report.append("\n## 7. 音频生成（已跳过）")

    # --- 8. validate ---
    report.append("\n## 8. 样本质量门（validate.py）")
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
    verdict = "✅ 通过：工具包端到端可用（样本过门 + 鲁棒性 + 曲线 + 锁定达标）" if overall else "❌ 未通过：见上述失败项，修工具包后重跑"
    report.insert(3, f"\n**结论：{verdict}**\n生成时间：{ts}\n")
    report.append(f"\n---\n**结论：{verdict}**")

    md = "\n".join(report)
    (root / "sample_validation_report.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"\n[run_sample_validation] report → {root / 'sample_validation_report.md'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
