"""真实冒烟：AI_RUNNER=claude 跑阶段 1（需求消化→问题单），人工核对问题单质量。

用法（repo 根）：
    cd app/backend && uv run python smoke_stage1.py [需求文档路径]
默认用 sample_data/2026-06-14-vocabulary-course-requirements.md。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "sample_data" / "2026-06-14-vocabulary-course-requirements.md"

os.environ["AI_RUNNER"] = "claude"
os.environ["WB_DATA_DIR"] = tempfile.mkdtemp(prefix="wb-smoke-")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # app/ —— 让 backend 包可导入

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import create_app  # noqa: E402


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    print(f"[smoke] runner=claude 文档={DOC.name}（{len(text)} 字）")
    with TestClient(create_app()) as client:
        r = client.post(
            "/api/products",
            json={
                "name": "词汇课程练习（冒烟）",
                "requirement_doc": text,
                "doc_name": DOC.name,
                "project": {"name": "手机App", "platform": "mobile_app"},
            },
        )
        r.raise_for_status()
        pid = r.json()["projects"][0]["id"]
        print(f"[smoke] project={pid} 发起阶段 1 任务…")
        t0 = time.monotonic()
        client.post(f"/api/projects/{pid}/stages/1/tasks").raise_for_status()

        last_state = ""
        while time.monotonic() - t0 < 420:
            d = client.get(f"/api/projects/{pid}").json()
            state = d["stage_status"]["1"]
            if state != last_state:
                print(f"[smoke] {time.monotonic() - t0:6.1f}s  state={state}")
                last_state = state
            if state in ("awaiting_decision", "failed_needs_human"):
                break
            time.sleep(3)

        task = client.get(f"/api/projects/{pid}/tasks/current").json()
        print(f"[smoke] 终态={state} attempts={task['attempts']} cost={task['cost_s']}s")
        if state != "awaiting_decision":
            print(f"[smoke] 失败原因：{task['error']}")
            return 1

        d = client.get(f"/api/projects/{pid}/decision/1").json()["data"]
        print(f"[smoke] 问题单：阻塞 {len(d['blocking'])} 题 / 默认假设 {len(d['defaults'])} 条 / 成功标准 {len(d['success_criteria'])} 条")
        for q in d["blocking"]:
            rec = [o["label"] for o in q["options"] if o["recommend"]]
            print(f"  {q['id']}  {q['text']}\n     推荐：{rec[0] if rec else '（无——gate 漏了？）'}")
        out = Path(os.environ["WB_DATA_DIR"]) / "questions-dump.json"
        out.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[smoke] PASS——问题单全量 dump：{out}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
