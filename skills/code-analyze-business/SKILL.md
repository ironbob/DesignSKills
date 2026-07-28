---
name: code-analyze-business
description: "Trigger only when the user explicitly asks to use this skill by name: `$code-analyze-business`, `code-analyze-business`, or a namespaced form ending in `:code-analyze-business`. Do not trigger from task similarity, business-analysis keywords, repository contents, or inferred intent. Reverse-engineers one implemented business capability into an evidence-linked current-state analysis, a PM-language requirements document, and black-box test cases."
---

# 分析业务：读懂"代码里这一项业务到底怎么跑的"

## 目的

读代码把一项业务讲清楚，并产出**三件套**（互相回链，`analysis` 是唯一事实源）。**先搞清这个 app 是什么、本业务在领域里的位置，再用业务语言（而非代码术语）讲需求与测试**：

1. **现状分析 `analysis.md`** —— 应用与领域定位 + 由什么触发、经哪些步骤、改了哪些数据、依赖谁、哪里有风险，主流程讲透异常/兜底/兼容，每条结论回链 `file:line`。
2. **反推需求 `requirements.md`** —— PM 视角：为谁解决什么问题、功能清单（优先级 + **业务语言验收标准** + **实现状态** + **实现锚点**）、明确不做、非功能约束、**实现与需求偏差**。
3. **测试用例 `test-cases.md`** —— 覆盖所有需求与边缘 case（Happy / Error / Edge），**Expected Result 用业务可观察断言**，file:line 归实现锚点。

三件套给新人上手 / 重构与技术债评估 / 验收与回归当事实源。未实现但推断应有的能力只进入 `gap_items`，不混进已实现功能清单，也不强造测试用例。

只回答一个问题：**这项业务现在到底是怎么实现的、满足了哪些需求**——不回答"该不该这么设计""要重构成什么样""新产品要做什么功能"。反推的是**已实现的需求**，不是未来需求。

三个核心特征：

1. **读码取证** —— 不照念类名、注释、路由名当结论；每条判断都追到真实调用链或代码行，找不到依据的标 `⚠ 未确认`，绝不混进正文当事实。
2. **单一业务聚焦** —— 只分析用户确认的那一项业务，不蔓延成全系统文档；范围未确认前不产出。
3. **三视角分层回链** —— 现状（analysis）/ 需求（requirements）/ 测试（test-cases）三层各自回链，analysis 是唯一事实源，requirements 与 test-cases 都从它派生并指回它。

```
自然语言业务描述 + 代码库 ──► [code-analyze-business] ──► docs/business-analysis/<日期>-<业务>-{analysis,requirements,test-cases}.md（三件套）
```

<HARD-GATE>
在业务范围（**应用画像 + 领域定位** + 代码地图 + 一句话业务边界）被用户确认前，不进入深挖或正式产出。若用户首轮已明确给出业务名、入口/路径和包含/排除边界，视为已确认，不重复提问；否则只发起一次合并确认。本 skill 自己产出三件套，不调用其他 skill。
</HARD-GATE>

## 轻量执行策略

默认采用自适应深度，减少等待和冗余：

1. **一次确认**：只在范围不完整时，把业务文档询问、应用画像、领域锚点、代码地图和边界合并成一个确认包；不先问文档再单独确认范围。
2. **自动降级**：先探测 LSP；不可用就直接用 `rg`/文本搜索继续，并在进度与 analysis 中标注降级。只有降级结果产生实质歧义时才向用户求助，不因安装工具暂停。
3. **风险驱动测试**：硬卡每个已实现/部分实现功能至少一个用例、全局三类齐全、analysis 标“有”的完整性项被覆盖；不再机械要求每个 P0 都造 Happy/Error/Edge 三条。
4. **按复杂度收缩**：小业务允许短文档、少量概念和“不适用”矩阵行；复杂或高风险业务再展开状态机、额外图和更多边缘用例。5-pass 仍须执行，但可用一张紧凑表交付。
5. **按阶段加载参考**：定位阶段只读领域/定位参考，深挖阶段只读追踪/覆盖参考，生成阶段再读对应模板，避免一次加载全部材料。

## 边界（最重要）

**产出①（现状层 analysis.md）**：
- 应用与领域定位（应用画像 / 整体架构 / 领域定位 / 行业惯例锚点）、业务概述、触发与入口、核心领域概念、主流程（Mermaid + 回链 + **每步异常/兜底/兼容**）、**异常·兜底·兼容专项矩阵**、**链路覆盖（5-pass：入口/调用链/反向引用/数据副作用/横切）**、数据与存储（**含数据流动图 + 关键字段字典**）、依赖与耦合、风险与技术债、代码地图（详见 `references/analysis-template.md`）

**产出②（反推需求 requirements.md + requirements.json，PM 视角）**：
- 一句话目标、目标用户（主要/次要/**NOT**）、核心场景
- 功能清单 ★（仅已实现/部分实现：**REQ id** `REQ-<MODULE>-<n>` + 优先级 P0/P1/P2 + 功能 + 简述 + **验收标准（业务语言，可判定）** + **实现状态** ✅/⚠️ + **实现锚点**）
- 明确不做、非功能约束
- **实现与需求偏差** ★（反推独有：代码做了但需求未必需要的 / 需求该有但代码缺失的）
- 已知缺口（用 `GAP-<MODULE>-<n>` 独立编号，不进入功能清单，详见 `references/requirements-template.md`）
- **`requirements.json`**：`features` 保存已实现/部分实现功能，`gap_items` 保存未实现缺口；只有 REQ id 是 test-cases 回链的 join key

**产出③（测试用例 test-cases.md + test-cases.json）**：
- 按 Module 组织，每个用例 `TC-<MODULE>-<n>` / Type（Happy / Error / Edge）/ Preconditions / Steps / **Expected Result（业务可观察断言）** + **实现锚点（file:line）** / 需求来源（指向**具体功能** REQ id）
- **覆盖规则（`validate_contract.py` 机器校验）**：每个 `features` 功能 ≥1 用例（孤儿=ERROR）+ Happy/Error/Edge 全局各 ≥1（ERROR）；analysis 标「有」的完整性项各 ≥1 用例（ERROR，靠 case 的 `covers` 登记）。`gap_items` 不生成用例。
- **`test-cases.json`**：把用例结构化为契约源（req/type/anchor/covers），让覆盖与引用完整性可精确校验（详见 `references/test-cases-template.md`）

**不产出**（超出本 skill 范围，记入"已知缺口"即可）：
- ❌ 重构方案或新设计：只记现状与风险，不提"应该怎么改"
- ❌ **正向新产品需求**：反推的是**已实现的需求**，不是 clarify-requirements 的"要做什么"
- ❌ 可执行测试代码：只产语言无关的自然语言用例（栈绑定的 Playwright 代码是 web-test-case-man 的事）
- ❌ 渲染排版：多后端渲染是 doc-render 的事
- ❌ 全系统文档：只聚焦确认的那一项业务

**越界拉回**：当对话滑向"这块该不该重构成 XX""加个新功能""这份文档要发 Confluence 什么格式""帮我写 pytest"时，明确说"这超出业务分析的范围，只记录现状与缺口"，记一笔到"已知缺口"，不在本阶段展开。

## Checklist

按 6 个阶段完成；只有“范围不明确”会触发一次用户等待：

1. **定位并合并确认** —— 只读仓库信号，建立代码地图、应用/领域画像和候选边界。仅当范围需要确认时，才在同一个确认包中顺带询问业务文档；用户首轮信息已完整则直接进入下一步，不为缺文档单独暂停。读 `domain-profiling.md` + `locating-business.md`。
2. **深挖与覆盖** —— 在确认边界内追主流程、领域概念、状态与数据；做 5-pass。LSP 不可用时自动文本搜索降级。读 `tracing-flow.md` + `coverage-strategy.md`。
3. **完成 analysis** —— 收敛异常/兜底/兼容矩阵、数据/依赖/风险和完整性 5 项，按 `analysis-template.md` 写文档并运行 `validate_analysis.py`。
4. **反推 requirements** —— `features` 只收 ✅/⚠️，推断但未实现的能力写入 `gap_items`；按 `reverse-prd.md` + `requirements-template.md` 生成 md/json 并运行两个 requirements 校验器。
5. **派生 test-cases** —— 只给 `features` 生成风险驱动用例，不给 `gap_items` 造用例；按 `test-case-generation.md` + `test-cases-template.md` 生成 md/json 并运行两个 test-cases 校验器。
6. **契约与交付** —— 运行 `validate_contract.py`；人工抽检回链真实性、图边、MD/JSON 一致性和未确认隔离。全部通过才交付。

## 产出文档

三件套 md + 两份 JSON 契约源存到 `docs/business-analysis/`，共享 `<日期>-<业务名>` 前缀（业务名用 kebab-case 英文，日期用当天）：

- `YYYY-MM-DD-<业务名>-analysis.md`（现状，用 `references/analysis-template.md`）
- `YYYY-MM-DD-<业务名>-requirements.md`（反推需求，用 `references/requirements-template.md`）
- `YYYY-MM-DD-<业务名>-requirements.json`（**功能清单契约源**：每条功能带稳定 `REQ-<MODULE>-<n>` id）
- `YYYY-MM-DD-<业务名>-test-cases.md`（测试用例，用 `references/test-cases-template.md`）
- `YYYY-MM-DD-<业务名>-test-cases.json`（**用例契约源**：每条用例的 req / type / anchor / covers）

md 是给人读的渲染，json 是给校验器读的契约源，**两者必须一致**（json validator 会对账）。交付前各自跑校验脚本且合格。校验脚本在本 skill 的 `scripts/` 目录（与 SKILL.md 同级）——**不要假设当前目录是仓库根**：作为 corin 插件加载时路径为 `${CLAUDE_PLUGIN_ROOT}/skills/code-analyze-business/scripts/`，否则按本 SKILL.md 所在目录拼出同级 `scripts/` 的绝对路径再运行。

```bash
V="${CLAUDE_PLUGIN_ROOT}/skills/code-analyze-business/scripts"   # 非插件：用本 SKILL.md 同级 scripts/ 的绝对路径
python3 "$V/validate_analysis.py"            <analysis.md>
python3 "$V/validate_requirements.py"        <requirements.md>
python3 "$V/validate_requirements_json.py"   <requirements.json> <requirements.md>
python3 "$V/validate_test_cases.py"          <test-cases.md>
python3 "$V/validate_test_cases_json.py"     <test-cases.json>   <test-cases.md>
python3 "$V/validate_contract.py"            <requirements.json> <test-cases.json> <analysis.md>
```

## 参考资源

**analysis（现状层）**
- **`references/domain-profiling.md`** —— 仓库画像、领域定位、行业惯例来源与合并确认，阶段 1 用
- **`references/locating-business.md`** —— 从自然语言定位业务入口 + 建代码地图，阶段 1 用
- **`references/tracing-flow.md`** —— 主流程/数据流、领域概念、图文双轨与回链格式，阶段 2 用
- **`references/coverage-strategy.md`** —— 5-pass 链路覆盖（入口/调用链/反向引用/数据副作用/横切）+ LSP/文本搜索自动降级协议，阶段 2 用
- **`references/analysis-template.md`** —— 现状文档完整模板（frontmatter 含领域字段 + 领域定位 preamble + 9 章节 + 异常·兜底·兼容矩阵）+ 端到端示例（订单退款）
- **`references/quality-rules.md`** —— 防臆造、完整性清单、banned 词与人工抽检，阶段 3/6 用

**requirements（反推需求层）**
- **`references/requirements-template.md`** —— 反推需求模板、features/gap_items 契约与示例，阶段 4 用
- **`references/reverse-prd.md`** —— 现状→PM 需求翻译、实现状态与偏差分析，阶段 4 用

**test-cases（测试层）**
- **`references/test-cases-template.md`** —— 测试用例模板与 JSON 契约，阶段 5 用
- **`references/test-case-generation.md`** —— 风险驱动覆盖、边缘 case 与黑盒断言，阶段 5 用

**校验脚本**
- `scripts/validate_analysis.py` —— analysis 现状层交付前必跑
- `scripts/validate_requirements.py` / `validate_requirements_json.py` —— requirements 的 md 渲染 + json 契约源
- `scripts/validate_test_cases.py` / `validate_test_cases_json.py` —— test-cases 的 md 渲染 + json 契约源
- `scripts/validate_contract.py` —— req.json ↔ test-cases.json 跨文件契约（引用完整性 / 孤儿功能 / 覆盖 / 完整性）
