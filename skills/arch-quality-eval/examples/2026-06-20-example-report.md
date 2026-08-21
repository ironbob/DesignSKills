---
schema_version: 2
module: order-service
title: order-service 架构设计质量诊断
language: JVM
analyzed_at: 2026-06-20
scope_files:
  - src/main/java/com/x/order/OrderController.java
  - src/main/java/com/x/order/OrderRepository.java
  - src/main/java/com/x/order/OrderService.java
  - src/main/java/com/x/promotion/PromotionService.java
indexed_file_count: 4
inspected_file_count: 4
semantic_resolved_file_count: 0
coverage_sufficient: false
conventions_fed: false
no_go_threshold: 1
verdict: no-go
critical_count: 1
major_count: 1
minor_count: 1
confirmed_critical_count: 1
cpp_limitation_noted: false
open_questions: 1
status: draft
---

# order-service 架构设计质量诊断

> 以复杂度管理、职责边界、依赖、信息隐藏、抽象一致性和变化隔离为主轴；不检查语法、语言技巧、lint 或 CI。

## 一、范围与覆盖

- **路径**：`src/main/java/com/x/order`、`src/main/java/com/x/promotion/PromotionService.java`。
- **职责基线**：负责订单查询、内部促销重算以及促销侧订单状态访问。
- **结构**：Java 包 com.x.order / com.x.promotion，包含 controller、service、repository 角色。
- **覆盖**：范围 4，索引 4，精读 4，语义解析 0 个文件。
- **结论覆盖充分性**：不足。

## 二、诊断结论

**⛔ no-go** —— confirmed critical 1，阈值 1。

critical 候选：

- `FINDING-D01` order 与 promotion 包级循环依赖（confidence=confirmed）：包级依赖环影响两个模块角色并阻塞拆分，因此为 critical。

## 三、设计原则矩阵

| 设计轴 | 状态 | 结论 | 代表证据 |
|---|---|---|---|
| 复杂度管理 (`complexity-management`) | ✅ no material concern | 现有证据没有证明单个类型因规模或间接层造成独立的复杂度集中问题。 | src/main/java/com/x/order/OrderService.java:3 |
| 职责与内聚 (`responsibility-cohesion`) | ⚠ concern | Controller 直接承担仓储查询，使请求适配与数据访问编排混在同一职责中。 | src/main/java/com/x/order/OrderController.java:33 |
| 耦合与依赖方向 (`coupling-dependency-direction`) | ⚠ concern | order 与 promotion 双向依赖，且 Controller 绕过 Service 直接依赖 Repository。 | src/main/java/com/x/order/OrderService.java:42 / src/main/java/com/x/promotion/PromotionService.java:18 |
| 信息隐藏与接口边界 (`information-hiding`) | ⚠ concern | 内部促销重算操作作为 public 方法暴露，扩大了非必要兼容面。 | src/main/java/com/x/order/OrderService.java:120 |
| 抽象层级一致性 (`abstraction-consistency`) | ⚠ concern | Controller 的请求层职责中混入 Repository 访问机制。 | src/main/java/com/x/order/OrderController.java:33 |
| 变化隔离与可演进性 (`change-isolation`) | ❓ inconclusive | 没有提交历史，无法判断订单变化是否长期散落在多个单元。 | — |

## 四、结构问题

#### FINDING-D01 · order 与 promotion 包级循环依赖 · 🔴 critical · confidence=confirmed

- 证据：`src/main/java/com/x/order/OrderService.java:42`（PromotionService）；`src/main/java/com/x/promotion/PromotionService.java:18`（OrderRepository）
- 违反原则：coupling-dependency-direction
- 关联规约：—
- 影响：两个包无法独立演进，循环边阻塞后续职责拆分。
- 分级依据：包级依赖环影响两个模块角色并阻塞拆分，因此为 critical。
- 改进方向：抽取稳定边界或反转其中一条依赖；完整设计留到重构阶段。
- 修复成本：high　优先级：P1（解除循环是其他边界治理的先决条件。）

#### FINDING-D02 · OrderController 直接依赖 OrderRepository · 🟠 major · confidence=confirmed

- 证据：`src/main/java/com/x/order/OrderController.java:12`（OrderRepository）；`src/main/java/com/x/order/OrderController.java:33`（OrderController calls orderRepository findByUserId）
- 违反原则：responsibility-cohesion、coupling-dependency-direction、abstraction-consistency
- 关联规约：—
- 影响：请求适配层掌握仓储机制，查询变化会直接传播到 Controller。
- 分级依据：影响主查询路径但可通过服务边界增量治理，因此为 major。
- 改进方向：让 Controller 只依赖表达查询能力的服务边界。
- 修复成本：low　优先级：P2（可独立治理，但不阻塞解除包级循环。）

#### FINDING-D03 · 内部促销重算操作形成不必要的 public 接口 · 🟡 minor · confidence=probable

- 证据：`src/main/java/com/x/order/OrderService.java:120`（recalcPromotion）
- 违反原则：information-hiding
- 关联规约：—
- 影响：调用方可能依赖内部重算步骤，扩大未来兼容面。
- 分级依据：只涉及一个接口，爆炸半径局部，因此为 minor。
- 改进方向：确认仓外调用后收紧可见性，或暴露更稳定的业务能力。
- 修复成本：low　优先级：P3（先补齐调用证据，再随相关接口修改处理。）

## 五、架构可理解性

**opaque** —— order 与 promotion 的双向依赖使上层方向无法快速解释，Controller 又混入仓储访问机制。

## 六、优先级

| 优先级 | finding | 排序依据 |
|---|---|---|
| P1 | FINDING-D01 | 解除循环是其他边界治理的先决条件。 |
| P2 | FINDING-D02 | 可独立治理，但不阻塞解除包级循环。 |
| P3 | FINDING-D03 | 先补齐调用证据，再随相关接口修改处理。 |

## 七、方法与缺口

- **取证方式**：文本索引/搜索；语言工具只提供架构证据。
- **聚焦策略**：先核对 order 与 promotion 双向依赖，再检查 Controller、Service 与 Repository 的职责边界。
- **Git 历史**：不可用或未采样。
- **未覆盖**：未采样历史提交；不评价语法、格式或 Java 语言技巧。
- **覆盖缺口**：未使用 Git 历史，变化隔离轴不能排除历史型协同修改。
- **已知缺口**：FINDING-D03：当前范围内未见调用方，但仓外调用未知，因此暴露影响置信度为 probable。
- **边界**：仅做重构前架构诊断；完整重构方案、语法检查和语言技巧不在范围内。
