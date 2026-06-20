---
module: order-service
title: 订单服务 架构质量诊断（重构前）
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
open_questions: 0
status: draft
---

# 订单服务（order-service）架构质量诊断报告

> 重构前诊断：本文只回答「要不要重构、先改哪里」，不回答「该不该这么设计/重构成什么样」，不提完整重构方案，不做 lint，不做 CI 卡关。

## 一、评估范围

- **路径与覆盖文件**：`src/main/java/com/x/order/`（order 包）+ `src/main/java/com/x/promotion/PromotionService.java`，共 4 个核心源文件（`covered_files` 见 frontmatter）。
- **语言与结构**：JVM（Java）。包结构 `com.x.order` / `com.x.promotion`，层按 controller / service / repository 划分。
- **项目规约**：未喂入（`conventions_fed: false`），只跑通用架构准则，不做项目规约对照。
- **模块职责（基线）**：order-service 负责订单的创建、退款与促销计算。

## 二、go/no-go 门禁结论

**⛔ no-go** —— 存在 1 个 critical 阻塞问题（critical 1 ≥ 阈值 1），建议先解 critical 再定重构范围。

- critical 项：`FINDING-S01` order↔promotion 包级循环依赖（阻塞两个包独立演进，也是 God Class 拆分的先决条件）。

一句话：模块可以演进，但循环依赖不解，后续拆分无从下手——**先解 S01，再谈 God Class 拆分**。

## 三、架构坏味道清单

核心坏味道覆盖矩阵（✅ 已检出 / ⬜ 未检出）：

| 核心坏味道 | 判定 | 证据锚点 |
|-----------|------|---------|
| 循环依赖 circular-dependency | ✅ 已检出 → FINDING-S01 | OrderService.java:42 / PromotionService.java:18 |
| God Class / God Package | ✅ 已检出 → FINDING-S02 | OrderService.java:1 |
| 跨层调用 cross-layer | ✅ 已检出 → FINDING-S03 | OrderController.java:33 |
| 霰弹式修改 shotgun-surgery | ⬜ 未检出（本模块未发现一改多散的强证据） | — |
| 不恰当暴露 inappropriate-exposure | ✅ 已检出 → FINDING-S04 | OrderService.java:120 |

#### FINDING-S01 · order 与 promotion 包级循环依赖 · 🔴 critical

- 证据：order→promotion `OrderService.java:42`（import `com.x.promotion.PromotionService` 并持有字段）；promotion→order `PromotionService.java:18`（import `com.x.order.OrderRepository` 查订单状态）。
- 违反原理：单向依赖原则。
- 影响：两个包无法独立编译、部署与演进，任一改动相互阻塞；循环边使 God Class 拆分无从下手，是重构主要阻塞点。
- 分级依据：包级循环依赖 → critical（阻塞重构）。
- 改进方向：抽 order/promotion 共用领域模型到独立 common 包，或用事件/接口由 promotion 反转对 order 的依赖（完整方案留重构阶段）。
- 修复成本：high　优先级：P1（先解循环，它是 S02 拆分的先决条件）。

#### FINDING-S02 · OrderService 承担下单/退款/促销多职责（模块中枢） · 🟠 major

- 证据：`OrderService.java:1` `OrderService` 单类 1200+ 行、38 个 public 方法，方法按下单/退款/促销三簇聚类；`OrderService.java:42` 促销依赖 `PromotionService` 混在订单服务类中。
- 违反原理：单一职责原则。
- 影响：三类变更挤进同一类，改动易相互牵连、回归面大；新人难以定位单一职责代码。
- 分级依据：核心中枢类职责混杂，但可局部拆分治理 → major。
- 改进方向：按职责拆为 OrderCreateService / OrderRefundService，促销计算下沉 promotion 包（依赖 S01 先解循环）。
- 修复成本：medium　优先级：P2。

#### FINDING-S03 · OrderController 跨层直接依赖 OrderRepository，绕过 Service · 🟠 major

- 证据：`OrderController.java:33` Controller 注入并直接调用 `orderRepository.findByUserId(...)`；`OrderController.java:12` import `com.x.order.OrderRepository`。
- 违反原理：分层不穿透原则。
- 影响：Controller 承担本属 Service 的查询编排，业务逻辑散落 Web 层，后续改动易漏走 Service。
- 分级依据：可插防腐层即可治理的跨层调用 → major。
- 改进方向：查询走 OrderQueryService 暴露的方法，Controller 只做参数转换与调用。
- 修复成本：low　优先级：P2。

#### FINDING-S04 · recalcPromotion 本应内部私有却对外 public 暴露 · 🟡 minor

- 证据：`OrderService.java:120` `public void recalcPromotion(...)` 仅为内部重算使用，无外部调用方。
- 违反原理：信息隐藏原则。
- 影响：内部重算方法成为隐式 API，外部误用即产生耦合，改动需排查全仓调用。
- 分级依据：个别方法暴露面问题，低爆炸半径 → minor。
- 改进方向：收紧为 private（或包级）；确有外部需要则显式定义到对外 API 包。
- 修复成本：low　优先级：P3。

## 四、架构可读性

只评架构层可读性，不含 lint 能查的代码风格（缩进、命名格式、import 顺序）。

| 轴 | 结论 | 证据 |
|----|------|------|
| 职责清晰度 | 一般偏下：OrderService 混合下单/退款/促销三职责，职责边界模糊 | OrderService.java:1 |
| 依赖可理解性 | 差：order 与 promotion 双向依赖，读者无法判断谁是上层 | OrderService.java:42 / PromotionService.java:18 |
| 命名表意度 | 一般：OrderManager / OrderHelper 不表意，看不出职责 | OrderManager.java:1 |
| 分层清晰度 | 一般：Controller 直连 Repository 穿透 Service，边界不清 | OrderController.java:33 |

总体可读性：**一般**。最影响可读性的一点是 order↔promotion 双向依赖（依赖可理解性差），解了 S01 同时改善可读性与可维护性。

## 五、重构优先级总览

| 优先级 | finding | 先改它的理由 |
|--------|---------|-------------|
| P1 | FINDING-S01 循环依赖 | 影响面大 + 阻塞：它是 S02 拆分的先决条件，不解则两个包无法独立演进；虽成本高但收益最大 |
| P2 | FINDING-S02 God Class、FINDING-S03 跨层 | 不阻塞、可增量：S01 解开后按职责拆 S02，S03 低成本可顺手插防腐层 |
| P3 | FINDING-S04 不恰当暴露 | 低成本局部问题，顺手收紧可见性即可 |

建议改动顺序：① 解 S01 循环依赖 → ② 拆 S02 God Class → ③ 治 S03 跨层（插防腐层）→ ④ 收紧 S04 可见性。每步指方向，完整方案留重构阶段。

## 六、评估方法与已知缺口

- **评估方法**：包结构/层按包声明与目录识别；依赖边按 import 与全限定类型引用取证（LSP 不可用时 rg 文本搜索降级）。聚焦策略为热点优先——先定位 OrderService（中枢）与 order↔promotion 依赖边，深度取证，非热点抽样确认无重大问题。
- **本次未喂入项目规约**，故不做规约对照（如需对照分层/边界/禁止依赖方向规则，喂入后可增 `axis: convention` 的 finding）。
- **已知缺口**：本报告所有 finding 的 `unconfirmed` 均为 false，无未确认项；霰弹式修改判定依赖 git 历史，本次仅按代码结构未发现强证据，标记未检出。
- **越界说明**：本报告是重构前诊断，不含完整重构方案、不做 CI 自动卡关、不做 lint/代码风格（指向 PRD §5 不做项）。
