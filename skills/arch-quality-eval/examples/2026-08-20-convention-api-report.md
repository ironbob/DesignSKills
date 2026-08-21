---
module: convention-api
title: API 暴露规约架构质量诊断
language: JVM
analyzed_at: 2026-08-20
covered_files:
  - src/main/java/com/x/api/OrderApi.java
conventions_fed: true
no_go_threshold: 1
verdict: go
critical_count: 0
major_count: 0
minor_count: 2
cpp_limitation_noted: false
open_questions: 0
status: draft
---

# convention-api 架构质量诊断报告

> 重构前诊断：只回答模块是否值得重构、阻塞点和优先顺序；不输出完整重构方案，不做 lint 或 CI 卡关。

## 一、评估范围

- **路径**：`src/main/java/com/x/api`。
- **覆盖文件**：1 个源文件，详见 frontmatter。
- **语言与结构**：JVM；单包 JVM API 示例，用于演示通用暴露坏味道与用户规约违规的双轴记录。
- **模块职责基线**：提供订单报价 API，并封装内部折扣重算。
- **项目规约**：已手工喂入并参与检查。

## 二、go/no-go 门禁结论

**✅ go** —— critical 0，阈值 1。

未发现达到 critical 的阻塞问题，可以按优先级增量治理。

## 三、架构坏味道清单

| 核心坏味道 | 判定 | 证据锚点 |
|---|---|---|
| 循环依赖 circular-dependency | ⬜ 未检出 | — |
| God Class / God Package | ⬜ 未检出 | — |
| 跨层调用 cross-layer | ⬜ 未检出 | — |
| 霰弹式修改 shotgun-surgery | ⬜ 未检出 | — |
| 不恰当暴露 inappropriate-exposure | ✅ 已检出 → FINDING-S01 | src/main/java/com/x/api/OrderApi.java:8 |

#### FINDING-S01 · 内部折扣重算方法被作为 public API 暴露 · 🟡 minor

- 证据：`src/main/java/com/x/api/OrderApi.java:8`（public recalculateDiscount exposes basePrice recalculation）
- 违反原理：信息隐藏原则
- 影响：内部实现成为外部可依赖接口，后续修改折扣计算时需要维持不必要的兼容面。
- 分级依据：仅影响单个方法的暴露面，爆炸半径局部，因此为 minor。
- 改进方向：收紧方法可见性，只保留真正面向调用方的 quote API。
- 修复成本：low　优先级：P3（局部低成本问题，可随下一次 API 修改处理。）

## 四、项目规约违规

- `CONV-API1` 内部折扣重算方法不得作为 public API 暴露：✅ 检出违规 → FINDING-C01

#### FINDING-C01 · recalculateDiscount 违反 CONV-API1 暴露规约 · 🟡 minor

- 证据：`src/main/java/com/x/api/OrderApi.java:8`（public recalculateDiscount basePrice violates internal API rule）
- 违反规约：CONV-API1
- 影响：项目约定的 API 边界被破坏，调用方可能依赖内部重算操作。
- 分级依据：违反一条局部 API 规约，但未影响跨模块主链路，因此为 minor。
- 改进方向：按 CONV-API1 收紧可见性，并仅通过 quote 暴露稳定能力。
- 修复成本：low　优先级：P3（与 FINDING-S01 同源，可在同一次低成本修改中一起消除。）

## 五、架构可读性

| 轴 | 结论 |
|---|---|
| 职责清晰度 | 一般：OrderApi 的报价职责清楚，但同时公开内部折扣重算入口（OrderApi.java:3 / OrderApi.java:8）。 |
| 依赖可理解性 | 清晰：单文件内没有外部类型依赖，调用关系直接（OrderApi.java:4）。 |
| 命名表意度 | 清晰：quote 与 recalculateDiscount 均能表达行为（OrderApi.java:4 / OrderApi.java:8）。 |
| 分层清晰度 | 一般：单文件无法形成完整分层判断，但 public API 与内部操作边界不清（OrderApi.java:8）。 |

总体可读性：**一般；代码结构简单，但 API 与内部操作的暴露边界不清**

## 六、重构优先级总览

| 优先级 | finding | 排序依据 |
|---|---|---|
| P3 | FINDING-S01、FINDING-C01 | FINDING-S01：局部低成本问题，可随下一次 API 修改处理。；FINDING-C01：与 FINDING-S01 同源，可在同一次低成本修改中一起消除。 |

## 七、评估方法与已知缺口

- **取证方式**：文本搜索降级。
- **聚焦策略**：读取唯一 API 类型，核对 public 暴露面并同时对照通用信息隐藏原则和 CONV-API1。
- **Git 历史**：未使用，历史型坏味道结论保持保守。
- **未覆盖**：单文件范围只能评估暴露面，无法评价跨包依赖结构。
- **已知缺口**：
  - 范围只有一个 API 类型，循环依赖、跨层和包级职责结论的覆盖有限。
- **边界**：仅做重构前诊断；完整重构设计、代码风格和 CI 门禁不在本报告范围。
