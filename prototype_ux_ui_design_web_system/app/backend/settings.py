"""运行配置（环境变量优先，本地单用户默认值）。

- data_dir：产品/项目工作区与 sqlite 的根目录（磁盘是唯一真相源）
- runner：claude=真实 CLI 子进程；mock=即时罐头产物（开发/测试）
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
    task_timeout_s: int = 360
    auto_redo_limit: int = 1  # P2-3：gate 不过自动重做一次再转人工


def get_settings() -> Settings:
    data_dir = Path(os.environ.get("WB_DATA_DIR", REPO_ROOT / ".workbench-data"))
    runner = os.environ.get("AI_RUNNER", "mock").strip().lower()
    if runner not in ("claude", "mock"):
        runner = "mock"
    return Settings(data_dir=data_dir, runner=runner, task_timeout_s=int(os.environ.get("WB_TASK_TIMEOUT_S", "360")))
