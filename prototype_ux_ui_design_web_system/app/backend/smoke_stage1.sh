#!/usr/bin/env bash
# 真实冒烟：用真 claude CLI 跑阶段 1（会消耗你的配额，约 1-2 分钟）
set -euo pipefail
cd "$(dirname "$0")"
exec uv run python smoke_stage1.py "$@"
