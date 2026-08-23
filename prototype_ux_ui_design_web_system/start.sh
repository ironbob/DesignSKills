#!/usr/bin/env bash
# 一键运行：自检依赖→自动安装→起双服务→自动开浏览器（http://localhost:5180）
# 环境变量（透传给后端）：
#   AI_RUNNER=claude   真实 claude CLI 生成（消耗配额）；默认 mock 罐头不烧配额
#   AI_REVIEWER=off    跳过 L2 评审（默认跟随 runner）
#   WB_DATA_DIR=...    数据目录（默认 <本目录>/.workbench-data）
set -euo pipefail
cd "$(dirname "$0")"

APP_DIR="$(pwd)/app"
BACKEND_URL="http://127.0.0.1:8000"
FRONTEND_URL="http://localhost:5180"

say() { printf '\033[1;36m[start]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[start]\033[0m %s\n' "$*" >&2; exit 1; }

# ── 1. 依赖自检 ───────────────────────────────────────────────
command -v uv  >/dev/null 2>&1 || die "缺 uv：brew install uv"
command -v npm >/dev/null 2>&1 || die "缺 npm：先装 Node.js（brew install node）"
command -v curl >/dev/null 2>&1 || die "缺 curl（健康探测用）"
if [[ "${AI_RUNNER:-mock}" == "claude" ]] && ! command -v claude >/dev/null 2>&1; then
  die "AI_RUNNER=claude 需要已登录的 claude CLI"
fi
say "依赖 OK：runner=${AI_RUNNER:-mock} reviewer=${AI_REVIEWER:-跟随 runner}"

# ── 2. 端口预检（8000/5180 被 vite 代理与 strictPort 锁死，URL 才是确定的）──
for p in 8000 5180; do
  if lsof -nP -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; then
    die "端口 $p 已被占用（可能是上次没退干净）：lsof -i :$p 排查后关闭"
  fi
done

# ── 3. 自动安装 ───────────────────────────────────────────────
say "同步后端环境（uv sync）…"
(cd "$APP_DIR/backend" && uv sync --quiet)
if [[ ! -d "$APP_DIR/frontend/node_modules" ]]; then
  say "首次安装前端依赖（较慢）…"
  (cd "$APP_DIR/frontend" && npm install --no-fund --no-audit --silent)
fi

# ── 4. 起双服务 + 自动开浏览器 ────────────────────────────────
BACKEND_PID=""
FRONTEND_PID=""
kill_tree() {  # 先杀子进程（npm→node 这类包装层），再杀本体
  local pid="${1:-}"
  [[ -n "$pid" ]] || return 0
  pkill -TERM -P "$pid" 2>/dev/null || true
  kill -TERM "$pid" 2>/dev/null || true
}
cleanup() {
  trap - EXIT INT TERM
  kill_tree "$FRONTEND_PID"
  kill_tree "$BACKEND_PID"
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 后端：从 app/ 起才能按包导入 backend.main（相对导入）；mock 默认不烧配额
(cd "$APP_DIR" && AI_RUNNER="${AI_RUNNER:-mock}" exec uv run --project backend \
  uvicorn backend.main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

# 前端：vite :5180（strictPort），/api 代理到 :8000
(cd "$APP_DIR/frontend" && exec npm run dev) &
FRONTEND_PID=$!

# 等后端健康（uv 首次冷启动可能较慢）
say "等待后端就绪…"
for _ in $(seq 1 60); do
  if curl -sf --noproxy '*' --max-time 1 "$BACKEND_URL/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
curl -sf --noproxy '*' --max-time 1 "$BACKEND_URL/api/health" >/dev/null 2>&1 \
  || die "后端 60s 内未就绪（$BACKEND_URL/api/health），看上方 uvicorn 报错"
say "后端就绪：$BACKEND_URL"

# 开浏览器（macOS: open；Linux: xdg-open）
if command -v open >/dev/null 2>&1; then
  open "$FRONTEND_URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$FRONTEND_URL" >/dev/null 2>&1 || true
fi

say "启动完成：${FRONTEND_URL}（Ctrl+C 退出双服务）"
wait
