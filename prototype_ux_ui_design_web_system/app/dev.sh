#!/usr/bin/env bash
# 兼容别名：等价于仓库根的 start.sh（一键运行）
exec bash "$(dirname "$0")/../start.sh" "$@"
