"""运行配置（环境变量优先，本地单用户默认值）。

- data_dir：产品/项目工作区与 sqlite 的根目录（磁盘是唯一真相源）
- runner：claude=真实 CLI 子进程；mock=即时罐头产物（开发/测试）
- reviewer：L2 评审器。claude=真实 CLI 独立会话；mock=全绿罐头；off=跳过 L2（只 L1）
  默认跟随 runner（mock 配 mock、claude 配 claude），可单独覆盖
- auto_redo_limit：gate/评审打回共享的重试预算（P2-3 + 防 Goodhart 循环）
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    runner: str  # "claude" | "mock"
    reviewer: str  # "claude" | "mock" | "off"
    task_timeout_s: int
    auto_redo_limit: int = 1  # 打回自动重做一次再转人工（L1/L2 共享预算）


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("WB_DATA_DIR", REPO_ROOT / ".workbench-data"))
    runner = os.environ.get("AI_RUNNER", "mock").strip().lower()
    if runner not in ("claude", "mock"):
        runner = "mock"
    default_reviewer = "claude" if runner == "claude" else "mock"
    reviewer = os.environ.get("AI_REVIEWER", default_reviewer).strip().lower()
    if reviewer not in ("claude", "mock", "off"):
        reviewer = default_reviewer
    return Settings(
        data_dir=data_dir,
        runner=runner,
        reviewer=reviewer,
        task_timeout_s=int(os.environ.get("WB_TASK_TIMEOUT_S", "360")),
    )
