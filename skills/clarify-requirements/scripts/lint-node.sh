#!/usr/bin/env bash
# 领域节点结构校验：保证生成的节点能稳定作为 skill 引用（契约门）。
# 用法:
#   bash scripts/lint-node.sh                                    # 校验 domains/ 下所有节点
#   bash scripts/lint-node.sh references/domains/c-end/tools.md  # 校验指定节点（相对 skill 根）
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"        # skill 根目录
DOM="$ROOT/references/domains"
TOPO="$ROOT/references/domain-analysis.md"

# banned 词（与 _AUTHORING.md 第五节一致）
BANNED_RE='体验好|功能完善|功能强大|适当处理|待定|待补|后续再说|良好体验|非常重要|很关键|等等|TBD|TODO'

FAIL=0

sig_block() { awk '/^## 匹配信号/{p=1;next} /^## /{p=0} p' "$1"; }

lint_one() {
  local f="$1" errs=0 is_root=0 rel="${f#$ROOT/}"
  grep -q '继承：无（根节点）' "$f" && is_root=1
  echo "── $rel"

  # 1. 必备标题段
  local h
  for h in '## 匹配信号' '## 核心价值要素' '## 业界标配功能' '## 业界标杆做法' '## 常见陷阱与反模式' '## 本节点专属澄清'; do
    grep -qF "$h" "$f" || { echo "  ❌ 缺标题: $h"; errs=$((errs+1)); }
  done
  if [ "$is_root" = 0 ]; then
    grep -qF '## 继承要点' "$f" || { echo "  ❌ 非根节点缺: ## 继承要点"; errs=$((errs+1)); }
  else
    grep -qF '## 继承要点' "$f" && { echo "  ⚠️  根节点不应有: ## 继承要点"; errs=$((errs+1)); }
  fi

  # 2. header 行
  grep -qF '树路径：' "$f" || { echo "  ❌ 缺 header: 树路径"; errs=$((errs+1)); }
  grep -qF '继承：'    "$f" || { echo "  ❌ 缺 header: 继承";    errs=$((errs+1)); }
  [ "$is_root" = 0 ] && { grep -qF '使用前先读父类' "$f" || { echo "  ❌ 非根缺 header: 使用前先读父类"; errs=$((errs+1)); }; }

  # 3. 匹配信号：≥2 条；非根须有"关键词(≥3项) + 场景"
  local siglines
  siglines=$(sig_block "$f" | grep -cE '^- ' || true)
  [ "$siglines" -ge 2 ] || { echo "  ❌ 匹配信号 bullet < 2 (=$siglines)"; errs=$((errs+1)); }
  if [ "$is_root" = 0 ]; then
    sig_block "$f" | grep -qE '^- 关键词' || { echo "  ❌ 非根匹配信号缺 '关键词' 行"; errs=$((errs+1)); }
    sig_block "$f" | grep -qE '^- 场景'   || { echo "  ❌ 非根匹配信号缺 '场景' 行"; errs=$((errs+1)); }
    local kw seps
    kw=$(sig_block "$f" | grep -E '^- 关键词' || true)
    seps=$(printf '%s' "$kw" | grep -oE '[/、]' | wc -l | tr -d ' ')
    [ "$((seps+1))" -ge 3 ] || { echo "  ❌ 关键词 < 3 项 (=$((seps+1)))"; errs=$((errs+1)); }
  fi

  # 4. banned 词
  local hits
  hits=$(grep -nE "$BANNED_RE" "$f" || true)
  [ -z "$hits" ] || { echo "  ❌ banned 词命中:"; echo "$hits" | sed 's/^/      /'; errs=$((errs+1)); }

  # 5. 拓扑登记（domain-analysis.md 提到该文件相对路径）
  local filerel="${f#$DOM/}"
  grep -qF "$filerel" "$TOPO" || { echo "  ❌ 未登记进 domain-analysis.md 拓扑: $filerel"; errs=$((errs+1)); }

  [ "$errs" = 0 ] && echo "  ✅ 通过" || FAIL=1
}

if [ $# -gt 0 ]; then
  for a in "$@"; do
    case "$a" in /*) lint_one "$a" ;; *) lint_one "$ROOT/$a" ;; esac
  done
else
  while IFS= read -r f; do lint_one "$f"; done < <(find "$DOM" -name '*.md' ! -name '_*' | sort)
fi

echo ""
[ "$FAIL" = 0 ] && { echo "✅ 全部通过"; exit 0; } || { echo "❌ 存在失败项"; exit 1; }
