---
business: order-refund
title: 订单退款业务分析
summary: 用户对已支付订单发起退款，系统校验可退条件后调用第三方支付退款，并更新订单状态为已退款
codebase: order-service
entry_type: http
analyzed_at: 2026-06-16
status: example
open_questions: 2
---

# 订单退款业务分析

> 示例产出（代码路径为虚构），用于演示 `code-analyze-business` skill 的产出形态，也可作 `clarify-doc` / `doc-blueprint` 的事实源输入。

## 1. 业务概述

订单退款是订单生命周期的终态之一：用户对一笔已支付订单发起退款，系统校验可退条件（状态、金额），调用第三方支付执行真实退款，再把订单置为"已退款"。 —— 入口 `src/api/refund.py:42`

## 2. 触发与入口

- 触发方式：HTTP 接口，用户在前端"订单详情 → 申请退款"点击（`submitRefund`）触发 —— `web/views/order/Refund.vue:28`
- 入口：`POST /api/orders/{order_id}/refund` → `refund_handler()` —— `src/api/refund.py:42`

## 3. 核心领域概念

- **退款单（RefundRecord）**：一次退款申请的聚合根，记录退款金额、状态、关联订单 —— `src/model/refund_record.py:12`
- **订单状态（OrderStatus）**：枚举 `未支付(0)/已支付(1)/已退款(4)/已关闭(9)` —— `src/model/order.py:8`

## 4. 主流程

<!-- evidence: refund_handler @ src/api/refund.py:42 → RefundService.refund @ src/service/refund_service.py:88 → PaymentClient.call_refund @ src/clients/payment_client.py:55 -->
```mermaid
flowchart TD
    A[接收退款请求] --> B{订单可退?}
    B -->|是| C[计算退款金额]
    B -->|否| D[拒绝退款]
    C --> E[调用第三方退款]
    E --> F{退款成功?}
    F -->|是| G[更新订单状态]
    F -->|否| H[记录失败 入补偿队列]
```

1. **接收退款请求** —— 校验入参（order_id、金额）…… `src/api/refund.py:42`
2. **订单可退?** —— 查订单状态，仅"已支付(1)"可退 …… `src/service/refund_service.py:95`
3. **计算退款金额** —— 按退款规则算（全额 / 部分）…… `src/service/refund_service.py:110`
4. **调用第三方退款** —— 调 `PaymentClient.call_refund` …… `src/clients/payment_client.py:55`
5. **退款成功?** —— 据返回码判断 …… `src/service/refund_service.py:135`
6. **更新订单状态** —— 置为"已退款(4)" …… `src/repo/order_repo.py:120`

## 5. 分支与异常

- **订单不可退** —— 状态非"已支付"时抛 `OrderNotRefundableError`，返回 400 …… `src/service/refund_service.py:97`
- **第三方退款失败** —— 返回码非成功，捕获异常后置退款单为"失败"，进入补偿队列（不直接抛给用户）…… `src/service/refund_service.py:138`

## 6. 数据与存储

- 读：从 `orders` 表取订单（状态、金额）…… `src/repo/order_repo.py:60`
- 改：写 `refund_records` 表（退款单状态）、更新 `orders.status` —— `src/repo/order_repo.py:120`

<!-- evidence: OrderStatus 赋值点 @ src/service/refund_service.py:95 (校验) / :135 (退款后) / src/repo/order_repo.py:120 (落库) -->
```mermaid
stateDiagram-v2
    [*] --> 未支付
    未支付 --> 已支付: 支付成功
    已支付 --> 已退款: 退款成功
    已支付 --> 已关闭: 关单
    已退款 --> [*]
```

## 7. 依赖与耦合

- 上游：前端退款页（`web/views/order/Refund.vue`）调本接口 —— 跨边界点 `src/api/refund.py:42`
- 下游 / 外部：依赖支付中心 `PaymentClient`，超时 3s、失败重试 2 次 —— `src/clients/payment_client.py:55`

## 8. 风险与技术债

- **重复退款（并发 / 幂等）** → 同一订单并发退款可能双退；当前用 `refund_lock`（Redis 分布式锁）串行化 + `refund_records` 的 order_id 唯一索引共同保证幂等，key=order_id —— `src/service/refund_service.py:160`
- **部分退款拆单规则** → 是否支持一笔订单分多次部分退，规则未在代码中明确 ⚠ 未确认 —— `src/service/refund_service.py:110`
- **外部依赖补偿** → 支付中心超时后仅入补偿队列，补偿逻辑未在本业务内，依赖外部 job ⚠ 未确认 —— `src/service/refund_service.py:138`

## 9. 代码地图

| 角色 | 关键位置 | 职责 |
|------|----------|------|
| HTTP 入口 | `src/api/refund.py:42` | 接收退款请求、参数校验 |
| 领域服务 | `src/service/refund_service.py:88` | 退款决策、金额计算、并发控制 |
| 数据访问 | `src/repo/order_repo.py:120` | 改订单状态 |
| 外部依赖 | `src/clients/payment_client.py:55` | 调用第三方支付退款 |
| 模型 | `src/model/refund_record.py:12` | 退款单聚合根 |

## 完整性自检

- 异常分支：有 —— 订单不可退抛 `OrderNotRefundableError` `src/service/refund_service.py:97`；退款失败入补偿队列 `src/service/refund_service.py:138`
- 触发条件：有 —— 仅"已支付(1)"订单可退 `src/service/refund_service.py:95`
- 并发时序：有 —— `refund_lock` 串行化防双退 `src/service/refund_service.py:160`
- 外部依赖：有 —— 支付中心超时 3s、重试 2 次 `src/clients/payment_client.py:55`
- 幂等：有 —— `refund_records` 的 order_id 唯一索引保证幂等 `src/service/refund_service.py:160`

## 已知缺口

- **部分退款拆单规则**：`refund_service.py:110` 处的金额计算未体现是否支持拆单，需找产品 / 历史 PR 确认；当前按"单次全额或单次部分"理解。
- **补偿逻辑归属**：`refund_service.py:138` 失败后入补偿队列，但补偿 job 不在本业务代码内，未追踪其实现与重试上限。
