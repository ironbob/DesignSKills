---
schema_version: 2
module: convention-api
title: convention-api 架构设计质量诊断
language: JVM
analyzed_at: 2026-08-20
scope_files:
  - src/main/java/com/x/api/OrderApi.java
indexed_file_count: 1
inspected_file_count: 1
semantic_resolved_file_count: 1
coverage_sufficient: false
conventions_fed: true
no_go_threshold: 1
verdict: inconclusive
critical_count: 0
major_count: 0
minor_count: 1
confirmed_critical_count: 0
cpp_limitation_noted: false
open_questions: 0
status: draft
---

# convention-api 架构设计质量诊断

> 以复杂度管理、职责边界、依赖、信息隐藏、抽象一致性和变化隔离为主轴；不检查语法、语言技巧、lint 或 CI。

## 一、范围与覆盖

- **路径**：`src/main/java/com/x/api`。
- **职责基线**：提供订单报价 API，并封装内部折扣重算。
- **结构**：单文件 API 边界示例，只足以评价当前接口暴露。
- **覆盖**：范围 1，索引 1，精读 1，语义解析 1 个文件。
- **结论覆盖充分性**：不足。

## 二、诊断结论

**❓ inconclusive** —— confirmed critical 0，阈值 1。

未确认 critical，但覆盖不足，不能把当前结果解释为架构健康。

## 三、设计原则矩阵

| 设计轴 | 状态 | 结论 | 代表证据 |
|---|---|---|---|
| 复杂度管理 (`complexity-management`) | ✅ no material concern | 单文件当前流程没有额外间接层。 | src/main/java/com/x/api/OrderApi.java:3 |
| 职责与内聚 (`responsibility-cohesion`) | ✅ no material concern | 报价和内部重算属于同一价格职责。 | src/main/java/com/x/api/OrderApi.java:4 |
| 耦合与依赖方向 (`coupling-dependency-direction`) | ❓ inconclusive | 单文件范围无法评价跨模块依赖方向。 | — |
| 信息隐藏与接口边界 (`information-hiding`) | ⚠ concern | 内部折扣重算作为 public API 暴露。 | src/main/java/com/x/api/OrderApi.java:8 |
| 抽象层级一致性 (`abstraction-consistency`) | ✅ no material concern | 当前方法仍处于报价职责层级，没有混入存储或协议机制。 | src/main/java/com/x/api/OrderApi.java:4 |
| 变化隔离与可演进性 (`change-isolation`) | ❓ inconclusive | 没有历史和范围外调用证据，无法评价变化传播。 | — |

## 四、项目规约

| 规约 | 结果 |
|---|---|
| `CONV-API1` 内部折扣重算方法不得作为 public API 暴露 | 违规 → FINDING-D01 |

## 五、结构问题

#### FINDING-D01 · 内部折扣重算方法被作为 public API 暴露 · 🟡 minor · confidence=confirmed

- 证据：`src/main/java/com/x/api/OrderApi.java:8`（public recalculateDiscount exposes basePrice operation）
- 违反原则：information-hiding
- 关联规约：CONV-API1
- 影响：调用方可能依赖内部计算步骤，扩大未来兼容面。
- 分级依据：只影响一个 API 方法，爆炸半径局部，因此为 minor。
- 改进方向：收紧内部重算入口，只暴露稳定的 quote 能力。
- 修复成本：low　优先级：P3（局部低成本问题，可随下一次 API 修改处理。）

## 六、架构可理解性

**mixed** —— API 名称清楚，但内部操作与稳定对外能力的边界不清。

## 七、优先级

| 优先级 | finding | 排序依据 |
|---|---|---|
| P3 | FINDING-D01 | 局部低成本问题，可随下一次 API 修改处理。 |

## 八、方法与缺口

- **取证方式**：文本索引/搜索；语言工具只提供架构证据。
- **聚焦策略**：完整读取唯一 API 类型，同时按信息隐藏原则和 CONV-API1 核对暴露面。
- **Git 历史**：不可用或未采样。
- **未覆盖**：范围外依赖、调用方和提交历史未覆盖。
- **覆盖缺口**：单文件范围不足以排除模块级耦合、依赖方向和历史变化传播问题。
- **已知缺口**：范围仅含一个 API 类型，verdict 只能为 inconclusive。
- **边界**：仅做重构前架构诊断；完整重构方案、语法检查和语言技巧不在范围内。
