---
name: code-analyze-business
description: "This skill should be used when the user asks to '分析这块业务', '梳理业务逻辑', '读懂这个功能', 'analyze business logic', or 'trace business flow' for one implemented business capability in a codebase. It confirms scope first, then produces a three-part output set under docs/business-analysis/: an evidence-linked analysis (current state), a reverse-engineered requirements doc (PM view), and test cases covering all requirements and edge cases. Do not use for new requirements, doc writing, redesign plans, or quick code summaries."
---

# 分析业务：读懂"代码里这一项业务到底怎么跑的"

## 目的

读代码把一项业务讲清楚，并产出**三件套**（互相回链，`analysis` 是唯一事实源）：

1. **现状分析 `analysis.md`** —— 由什么触发、经哪些步骤、改了哪些数据、依赖谁、哪里有风险，每条结论回链 `file:line`。
2. **反推需求 `requirements.md`** —— PM 视角：为谁解决什么问题、功能清单（优先级 + 可判定验收标准 + **实现状态**）、明确不做、非功能约束、**实现与需求偏差**。
3. **测试用例 `test-cases.md`** —— 覆盖所有需求与边缘 case（Happy / Error / Edge），每个 Expected Result 回链 `file:line`。

三件套给新人上手 / 重构与技术债评估 / 验收与回归当事实源。

只回答一个问题：**这项业务现在到底是怎么实现的、满足了哪些需求**——不回答"该不该这么设计""要重构成什么样""新产品要做什么功能"。反推的是**已实现的需求**，不是未来需求。

三个核心特征：

1. **读码取证** —— 不照念类名、注释、路由名当结论；每条判断都追到真实调用链或代码行，找不到依据的标 `⚠ 未确认`，绝不混进正文当事实。
2. **单一业务聚焦** —— 只分析用户确认的那一项业务，不蔓延成全系统文档；范围未确认前不产出。
3. **三视角分层回链** —— 现状（analysis）/ 需求（requirements）/ 测试（test-cases）三层各自回链，analysis 是唯一事实源，requirements 与 test-cases 都从它派生并指回它。

```
自然语言业务描述 + 代码库 ──► [code-analyze-business] ──► docs/business-analysis/<日期>-<业务>-{analysis,requirements,test-cases}.md（三件套）
```

<HARD-GATE>
在业务范围（代码地图 + 一句话业务边界）被用户确认前，不进入任何深挖或产出动作（不写分析正文、不画流程图、不定章节、不反推需求）。本 skill 自己产出三件套，不调用任何其他 skill。
</HARD-GATE>

## 反模式：直接照着类名/路由名猜业务

`OrderService` 可能并不处理下单主流程（也许只是订单查询）；`/api/refund` 路由名也不能保证退款逻辑都在它里面。照念类名、路由名、表名当结论，是这类分析最常见的失真。简单业务也要走两段式确认——三件套可以不长，但必须先确认范围、且每条结论都回链代码。

## 边界（最重要）

**产出①（现状层 analysis.md）**：
- 业务概述、触发与入口、核心领域概念、主流程（Mermaid + 回链）、分支与异常、数据与存储、依赖与耦合、风险与技术债、代码地图（详见 `references/analysis-template.md`）

**产出②（反推需求 requirements.md，PM 视角）**：
- 一句话目标、目标用户（主要/次要/**NOT**）、核心场景
- 功能清单 ★（模块表：优先级 P0/P1/P2 + 功能 + 简述 + **可判定验收标准** + **实现状态** ✅/⚠️/❌ + 回链）
- 明确不做、非功能约束
- **实现与需求偏差** ★（反推独有：代码做了但需求未必需要的 / 需求该有但代码缺失的）
- 已知缺口（详见 `references/requirements-template.md`）

**产出③（测试用例 test-cases.md）**：
- 按 Module 组织，每个用例 `TC-<MODULE>-<n>` / Type（Happy / Error / Edge）/ Preconditions / Steps / **Expected Result（回链 file:line）** / 需求来源
- 覆盖规则：每个 P0 功能 ≥1 Happy+1 Error+1 Edge，P1 ≥1 Happy+1 Edge；analysis 完整性 5 项各 ≥1 用例（详见 `references/test-cases-template.md`）

**不产出**（超出本 skill 范围，记入"已知缺口"即可）：
- ❌ 重构方案或新设计：只记现状与风险，不提"应该怎么改"
- ❌ **正向新产品需求**：反推的是**已实现的需求**，不是 clarify-requirements 的"要做什么"
- ❌ 可执行测试代码：只产语言无关的自然语言用例（栈绑定的 Playwright 代码是 web-test-case-man 的事）
- ❌ 渲染排版：多后端渲染是 doc-render 的事
- ❌ 全系统文档：只聚焦确认的那一项业务

**越界拉回**：当对话滑向"这块该不该重构成 XX""加个新功能""这份文档要发 Confluence 什么格式""帮我写 pytest"时，明确说"这超出业务分析的范围，只记录现状与缺口"，记一笔到"已知缺口"，不在本阶段展开。

## Checklist

为以下每项创建一个 task，按序完成：

1. **复述并锁定业务描述** —— 用一句话重述要分析哪项业务，请用户确认或修正。
2. **定位 + 建代码地图（只读不深挖）** —— 从自然语言定位业务入口，建一张代码地图（关键文件 + 入口 `file:line` + 职责）。详见 `references/locating-business.md`。
3. **两段式确认（HARD-GATE）** —— 把代码地图 + 一句话业务范围（触发词 X / 入口 Y / 边界含 A 不含 B）呈现给用户确认。未确认不进下一步。最大风险是"找错业务"，这一步专门拦它。
4. **深挖主流程 + 领域概念** —— 在确认后的边界内，追踪主流程调用链、识别核心领域概念与状态机。详见 `references/tracing-flow.md`。
5. **补全分支/异常 + 数据/依赖 + 风险** —— 逐项过完整性清单（异常分支/触发条件/并发时序/外部依赖/幂等），每项给出"有/无/不适用 + 依据"。详见 `references/quality-rules.md`。
6. **自审（analysis）** —— 回链完整性、完整性清单 5 项、图有依据（0 臆造边）、banned 词、未确认隔离。发现问题就地修。详见 `references/quality-rules.md`。
7. **产出 analysis.md** —— 用 `references/analysis-template.md`，写到 `docs/business-analysis/YYYY-MM-DD-<业务名>-analysis.md`。跑 `python skills/code-analyze-business/scripts/validate_analysis.py <文件>`，通过才进下一步。
8. **反推需求 requirements.md** —— analysis 通过后，按 `references/reverse-prd.md` 把现状翻译成 PM 视角需求（对齐 `references/requirements-template.md`：功能清单每行带实现状态 + 可判定验收标准 + 回链；写「实现与需求偏差」节）。写到 `docs/business-analysis/YYYY-MM-DD-<业务名>-requirements.md`，跑 `validate_requirements.py`，通过才进下一步。
9. **派生测试用例 test-cases.md** —— 按 `references/test-case-generation.md`，从 requirements + analysis 生成覆盖所有需求与边缘 case 的用例（对齐 `references/test-cases-template.md`）。写到 `docs/business-analysis/YYYY-MM-DD-<业务名>-test-cases.md`，跑 `validate_test_cases.py`。
10. **三件套交叉自审 + 交付** —— 回链一致性（requirements/test-cases 都指回 analysis、用例指回需求项 REQ-...）、完整性映射（analysis 5 项 → 用例）、未确认隔离（⚠ 未确认 三文件均有对应缺口登记）。三文件均通过各自 validator 即完成。

## 流程图

```dot
digraph analyze {
  "复述并锁定业务描述" [shape=box];
  "定位+建代码地图" [shape=box];
  "呈现业务范围" [shape=box];
  "业务范围确认?" [shape=diamond];
  "深挖主流程+概念" [shape=box];
  "补分支/数据/依赖/风险" [shape=box];
  "自审(analysis)" [shape=box];
  "写analysis" [shape=box];
  "validate_analysis?" [shape=diamond];
  "反推requirements" [shape=box];
  "validate_requirements?" [shape=diamond];
  "派生test-cases" [shape=box];
  "validate_test_cases?" [shape=diamond];
  "三件套交叉自审" [shape=box];
  "结束" [shape=doublecircle];

  "复述并锁定业务描述" -> "定位+建代码地图";
  "定位+建代码地图" -> "呈现业务范围";
  "呈现业务范围" -> "业务范围确认?";
  "业务范围确认?" -> "呈现业务范围" [label="否,修订"];
  "业务范围确认?" -> "深挖主流程+概念" [label="是"];
  "深挖主流程+概念" -> "补分支/数据/依赖/风险";
  "补分支/数据/依赖/风险" -> "自审(analysis)";
  "自审(analysis)" -> "写analysis";
  "写analysis" -> "validate_analysis?";
  "validate_analysis?" -> "自审(analysis)" [label="否,修订"];
  "validate_analysis?" -> "反推requirements" [label="是"];
  "反推requirements" -> "validate_requirements?";
  "validate_requirements?" -> "反推requirements" [label="否,修订"];
  "validate_requirements?" -> "派生test-cases" [label="是"];
  "派生test-cases" -> "validate_test_cases?";
  "validate_test_cases?" -> "派生test-cases" [label="否,修订"];
  "validate_test_cases?" -> "三件套交叉自审" [label="是"];
  "三件套交叉自审" -> "结束";
}
```

**终态是"结束"：三件套均通过各自校验、交叉自审一致即完成。**

## 自审检查项

### analysis 自审（Checklist 第 6 步展开）

写完 analysis 后用新视角过一遍：

1. **回链完整性** —— 每条结论能否指到 `file:line`？指不到的必须标 `⚠ 未确认`，不能当事实写。
2. **完整性自检 5 项** —— 异常分支 / 触发条件 / 并发时序 / 外部依赖 / 幂等，每项是否在「完整性自检」节显式标注"有/无/不适用 + 依据"，不留空（脚本硬卡）。
3. **图有依据** —— Mermaid 图里每条边是否对回下方文字的真实调用链？0 臆造边。
4. **Banned 词** —— 全文是否含"体验好/功能完善/适当处理/待定/很重要"等空话？有就改成具体可核的说法。
5. **未确认隔离** —— 推断与代码事实是否分清？推断都标了 `⚠ 未确认` 且在"已知缺口"里有对应条目。

### 三件套交叉自审（Checklist 第 10 步展开）

1. **回链拓扑** —— requirements/test-cases 的 frontmatter 都声明了 `source_analysis`？test-cases 声明了 `source_requirements`？每个用例标了 `需求来源: REQ-...`？
2. **需求→用例映射** —— requirements §4 每个功能（尤其 P0/P1）在 test-cases 里都有对应用例？analysis 完整性 5 项每项都有对应用例？
3. **实现状态一致** —— requirements 的 ✅/⚠️/❌ 与 analysis 描述吻合？❌ 缺口在 analysis「已知缺口」有对应？
4. **未确认贯通** —— 三文件里的 `⚠ 未确认` 是否都在各自「已知缺口」登记？`gaps` 计数对得上？

发现问题就地修，不必重审。

## 产出文档

三件套存到 `docs/business-analysis/`，共享 `<日期>-<业务名>` 前缀（业务名用 kebab-case 英文，日期用当天）：

- `YYYY-MM-DD-<业务名>-analysis.md`（现状，用 `references/analysis-template.md`）
- `YYYY-MM-DD-<业务名>-requirements.md`（反推需求，用 `references/requirements-template.md`）
- `YYYY-MM-DD-<业务名>-test-cases.md`（测试用例，用 `references/test-cases-template.md`）

交付前三个文件各自跑校验脚本且合格：
```
python skills/code-analyze-business/scripts/validate_analysis.py     <analysis.md>
python skills/code-analyze-business/scripts/validate_requirements.py <requirements.md>
python skills/code-analyze-business/scripts/validate_test_cases.py   <test-cases.md>
```

## 关键原则

- **两段式确认** —— 先建地图 + 陈述范围请用户确认，再深挖；最大失败模式是找错业务。
- **读码取证** —— 每条结论回链 `file:line`；无依据标 `⚠ 未确认`，不臆造。
- **图文双轨** —— 图给骨架直觉，下方文字逐步骤回链；图里每条边都要有代码佐证。
- **单一业务聚焦** —— 只分析确认的那一项，不蔓延全系统。
- **只说现状不说方案** —— 记录"现在怎么跑的"与风险，不提"该重构成什么"。
- **PM 口吻 + 可判定验收** —— 反推需求时用产品语言，验收标准写成可核断言（"仅状态∈{已支付}且金额≤可退余额可退"），不写"做了校验"。
- **三件套分层回链** —— analysis 是唯一事实源，requirements/test-cases 派生并指回它；测试用例指回需求项。
- **语言无关** —— 前后端自适应，测试用例写行为/状态不绑 UI 框架。

## 反模式

| 反模式 | 正确做法 |
|--------|----------|
| 照念类名/路由名/表名当结论 | 追真实调用链，回链 `file:line` |
| 跳过两段式确认直接产出 | 业务范围确认前禁止深挖与产出 |
| 画代码里没有的边/节点 | 图每条边对回下方文字的真实调用 |
| 结论无回链 | 回链代码，或标 `⚠ 未确认` |
| 蔓延成全系统文档 | 只聚焦用户确认的那一项业务 |
| 只产 analysis，漏 requirements/test-cases | 三件套是默认完整产出 |
| 反推需求写成"要做的新功能" | 只反推已实现的需求，正向需求归 clarify-requirements |
| requirements 验收标准写空话（"做了校验"） | 写可判定断言 + 回链 |
| 不写「实现与需求偏差」节 | 反推 PRD 必有偏差节（过度实现 / 需求缺口） |
| test-cases 的 Expected Result 不回链 | 必回链 `file:line`，既是用例也是行为规约 |
| 生成 Playwright/pytest 可执行代码 | 只产语言无关自然语言用例，可执行代码归栈绑定下游 |
| 假设并调用某个下游 skill | 本 skill 独立，结束即终止 |

## 参考资源

**analysis（现状层）**
- **`references/locating-business.md`** —— 怎么从自然语言定位业务入口 + 建代码地图，Checklist 第 2 步用
- **`references/tracing-flow.md`** —— 怎么追踪主流程/数据流、识别领域概念、Mermaid 选型与图文双轨、回链格式，第 4 步用
- **`references/analysis-template.md`** —— 现状文档完整模板（frontmatter + 9 章节）+ 端到端示例（订单退款）
- **`references/quality-rules.md`** —— 防臆造 3 原则、完整性自检清单 5 项、banned 词、专业 6 规则，第 5/6 步用

**requirements（反推需求层）**
- **`references/requirements-template.md`** —— 反推需求文档模板（frontmatter + 8 节，含实现状态列与偏差节）+ 端到端示例，第 8 步用
- **`references/reverse-prd.md`** —— 现状→PM 需求的翻译规则、实现状态判定、偏差分析方法，第 8 步用

**test-cases（测试层）**
- **`references/test-cases-template.md`** —— 测试用例文档模板（frontmatter + 模块化结构）+ 端到端示例，第 9 步用
- **`references/test-case-generation.md`** —— 覆盖规则、边缘 case 推导清单、完整性 5 项→用例映射，第 9 步用

**校验脚本**
- `scripts/validate_analysis.py` / `validate_requirements.py` / `validate_test_cases.py` —— 三件套各自交付前必跑
