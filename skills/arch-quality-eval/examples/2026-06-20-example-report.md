---
module: order-service
title: order-service 架构质量诊断（重构前）
language: JVM
analyzed_at: 2026-06-20
covered_files:
  - src/main/java/com/x/order/OrderService.java
  - src/main/java/com/x/order/OrderController.java
  - src/main/java/com/x/order/OrderRepository.java
  - src/main/java/com/x/promotion/PromotionService.java
conventions_fed: false
no_go_threshold: 1
verdict: no-go
critical_count: 1
major_count: 2
minor_count: 1
cpp_limitation_noted: false
open_questions: 0
status: draft
---

# order-service 架构质量诊断报告

> 重构前诊断：只回答模块是否值得重构、阻塞点和优先顺序；不输出完整重构方案，不做 lint 或 CI 卡关。

## 一、评估范围

- **路径**：`src/main/java/com/x/order`、`src/main/java/com/x/promotion/PromotionService.java`。
- **覆盖文件**：4 个源文件，详见 frontmatter。
- **语言与结构**：JVM；Java 包 com.x.order / com.x.promotion，按 controller / service / repository 分层。
- **模块职责基线**：order-service 负责订单创建、退款与促销计算。
- **项目规约**：未喂入，只检查通用架构准则。

## 二、go/no-go 门禁结论

**⛔ no-go** —— critical 1，阈值 1。

critical 项：

- `FINDING-S01` order 与 promotion 包级循环依赖：包级循环依赖阻塞两个包独立演进，也阻塞后续职责拆分，因此为 critical。

## 三、架构坏味道清单

| 核心坏味道 | 判定 | 证据锚点 |
|---|---|---|
| 循环依赖 circular-dependency | ✅ 已检出 → FINDING-S01 | src/main/java/com/x/order/OrderService.java:42 |
| God Class / God Package | ✅ 已检出 → FINDING-S02 | src/main/java/com/x/order/OrderService.java:1 |
| 跨层调用 cross-layer | ✅ 已检出 → FINDING-S03 | src/main/java/com/x/order/OrderController.java:33 |
| 霰弹式修改 shotgun-surgery | ⬜ 未检出 | — |
| 不恰当暴露 inappropriate-exposure | ✅ 已检出 → FINDING-S04 | src/main/java/com/x/order/OrderService.java:120 |

#### FINDING-S01 · order 与 promotion 包级循环依赖 · 🔴 critical

- 证据：`src/main/java/com/x/order/OrderService.java:42`（order 包 import com.x.promotion.PromotionService 并持有字段）；`src/main/java/com/x/promotion/PromotionService.java:18`（promotion 包 import com.x.order.OrderRepository 查订单状态）
- 违反原理：单向依赖原则
- 影响：两个包无法独立编译、部署与演进，任一改动相互阻塞；循环边使后续 God Class 拆分无从下手，是重构的主要阻塞点。
- 分级依据：包级循环依赖阻塞两个包独立演进，也阻塞后续职责拆分，因此为 critical。
- 改进方向：抽取 order/promotion 共用的领域模型到独立 common 包，或用事件/接口由 promotion 反转对 order 的依赖（完整方案留重构阶段定）。
- 修复成本：high　优先级：P1（影响面大且是其他拆分工作的先决条件，需最先解除。）

#### FINDING-S02 · OrderService 承担下单/退款/促销多职责，是模块中枢 · 🟠 major

- 证据：`src/main/java/com/x/order/OrderService.java:1`（OrderService 单类 1200+ 行、38 个 public 方法，方法按下单/退款/促销三簇聚类）；`src/main/java/com/x/order/OrderService.java:42`（促销依赖 PromotionService 混在订单服务类中）
- 违反原理：单一职责原则
- 影响：三类变更都挤进同一类，改动易相互牵连、回归面大；新人难以定位单一职责的代码。
- 分级依据：职责混杂影响核心类，但可在解除循环后增量拆分，因此为 major。
- 改进方向：按职责拆分为 OrderCreateService / OrderRefundService，促销计算下沉到 promotion 包（依赖 FINDING-S01 先解循环）。
- 修复成本：medium　优先级：P2（影响面大但依赖 FINDING-S01 先完成，排在第二批。）

#### FINDING-S03 · OrderController 跨层直接依赖 OrderRepository，绕过 Service · 🟠 major

- 证据：`src/main/java/com/x/order/OrderController.java:33`（Controller 注入并直接调用 orderRepository.findByUserId(...)）；`src/main/java/com/x/order/OrderController.java:12`（import com.x.order.OrderRepository）
- 违反原理：分层不穿透原则
- 影响：Controller 承担本属 Service 的查询编排，业务逻辑散落 Web 层，分层约束被旁路，后续改动漏走 Service。
- 分级依据：跨层调用影响主查询链路，但可以通过服务接口增量治理，因此为 major。
- 改进方向：查询走 OrderQueryService 暴露的方法，Controller 只做参数转换与调用；可插防腐层即可治理。
- 修复成本：low　优先级：P2（成本低且可独立治理，但不阻塞其他重构。）

#### FINDING-S04 · OrderService.recalcPromotion 本应内部私有却对外 public 暴露 · 🟡 minor

- 证据：`src/main/java/com/x/order/OrderService.java:120`（public void recalcPromotion(...) 仅为内部重算使用，无外部调用方）
- 违反原理：信息隐藏原则
- 影响：内部重算方法成为隐式 API，外部一旦误用即产生耦合，改动该方法需排查全仓调用。
- 分级依据：单个方法的暴露面问题，爆炸半径局部，因此为 minor。
- 改进方向：收紧为 private（或包级）；确有外部需要则显式定义到对外 API 包。
- 修复成本：low　优先级：P3（局部低风险问题，可在相关修改中顺手处理。）

## 四、架构可读性

| 轴 | 结论 |
|---|---|
| 职责清晰度 | OrderService 同时承担下单、退款、促销计算三职责，职责边界模糊（OrderService.java:1）。 |
| 依赖可理解性 | order 与 promotion 双向依赖，依赖方向不可理解，读者无法判断谁是上层（OrderService.java:42 / PromotionService.java:18）。 |
| 命名表意度 | OrderController 与 OrderRepository 能表达层级职责，命名表意清楚（OrderController.java:3 / OrderRepository.java:3）。 |
| 分层清晰度 | Controller 直接调用 Repository，穿透 Service 层，分层边界不清（OrderController.java:33）。 |

总体可读性：**一般；循环依赖最影响理解，职责和分层也存在局部混杂**

## 五、重构优先级总览

| 优先级 | finding | 排序依据 |
|---|---|---|
| P1 | FINDING-S01 | FINDING-S01：影响面大且是其他拆分工作的先决条件，需最先解除。 |
| P2 | FINDING-S02、FINDING-S03 | FINDING-S02：影响面大但依赖 FINDING-S01 先完成，排在第二批。；FINDING-S03：成本低且可独立治理，但不阻塞其他重构。 |
| P3 | FINDING-S04 | FINDING-S04：局部低风险问题，可在相关修改中顺手处理。 |

## 六、评估方法与已知缺口

- **取证方式**：文本搜索降级。
- **聚焦策略**：先定位 OrderService 中枢与 order↔promotion 依赖边，再对非热点文件做结构抽样。
- **Git 历史**：未使用，历史型坏味道结论保持保守。
- **未覆盖**：未使用 Git 历史验证霰弹式修改，只按当前代码结构保守判断。
- **已知缺口**：无未确认项。
- **边界**：仅做重构前诊断；完整重构设计、代码风格和 CI 门禁不在本报告范围。
