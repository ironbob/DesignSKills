---
business: order-refund
title: 订单退款测试用例
analyzed_at: 2026-06-16
status: example
source_analysis: 2026-06-16-order-refund-analysis.md
source_requirements: 2026-06-16-order-refund-requirements.md
total_cases: 9
by_type: {happy: 2, error: 3, edge: 4}
---

# 订单退款测试用例

> 源自 analysis：`2026-06-16-order-refund-analysis.md` ／ 源自 requirements：`2026-06-16-order-refund-requirements.md`
> 生成日期：2026-06-16　用例总数：9（Happy 2 / Error 3 / Edge 4）

## Module: REFUND（退款）

> 覆盖 requirements §4「退款发起」「可靠性」模块。

### TC-REFUND-01: 已支付订单全额退款

**Type:** Happy Path
**需求来源:** REQ-REFUND-01（requirements §4）
**Preconditions:** 存在 order_id=100，状态=已支付(1)，金额=100。

**Steps:**
1. 对 order_id=100 发起全额退款（amount=100）。

**Expected Result:** 退款单创建且状态=成功；orders.status 置为已退款(4)。 ……`src/repo/order_repo.py:120`

### TC-REFUND-02: 已支付订单部分退款

**Type:** Happy Path
**需求来源:** REQ-REFUND-01
**Preconditions:** order_id=100，状态=已支付(1)，金额=100。

**Steps:**
1. 对 order_id=100 发起部分退款（amount=30）。

**Expected Result:** 退款金额 30 被计算并提交第三方；退款单记录金额=30。 ……`src/service/refund_service.py:110`

### TC-REFUND-03: 已退款订单再次退款

**Type:** Error Flow
**需求来源:** REQ-REFUND-01
**Preconditions:** order_id=100，状态=已退款(4)。

**Steps:**
1. 对 order_id=100 再次发起退款。

**Expected Result:** 请求被拒，返回 400 + `OrderNotRefundableError`；订单状态不变。 ……`src/service/refund_service.py:97`

### TC-REFUND-04: 退款金额超过可退余额

**Type:** Error Flow
**需求来源:** REQ-REFUND-01
**Preconditions:** order_id=100，状态=已支付(1)，金额=100，已部分退款 30（可退余额=70）。

**Steps:**
1. 对 order_id=100 发起退款（amount=80，> 余额 70）。

**Expected Result:** 请求被拒（金额超可退余额）；不调第三方、不建退款单。 ……`src/service/refund_service.py:110`

### TC-REFUND-05: 第三方支付退款失败

**Type:** Error Flow
**需求来源:** REQ-REFUND-01
**Preconditions:** order_id=100，状态=已支付(1)；`PaymentClient.call_refund` 返回失败码。

**Steps:**
1. 对 order_id=100 发起全额退款。
2. 第三方连续重试 2 次仍失败。

**Expected Result:** 退款单置为"失败"并入补偿队列；不向用户直接报错；订单状态保持已支付(1)。 ……`src/service/refund_service.py:138`

### TC-REFUND-06: 退款请求参数缺失

**Type:** Edge Case
**需求来源:** REQ-REFUND-01
**Preconditions:** 无。

**Steps:**
1. 对 order_id=100 发起退款但未传 amount。

**Expected Result:** 入参校验拦截，返回 400；不进入业务逻辑。 ……`src/api/refund.py:42`

### TC-REFUND-07: 同一订单并发双退

**Type:** Edge Case
**需求来源:** REQ-REFUND-01（幂等）
**Preconditions:** order_id=100，状态=已支付(1)；两个全额退款请求同时到达。

**Steps:**
1. 并发发起两次全额退款（同 order_id）。

**Expected Result:** 仅一次成功，第二次被拒（Redis 锁 key=order_id 串行化 + refund_records.order_id 唯一索引）。 ……`src/service/refund_service.py:160`

### TC-REFUND-08: 第三方退款调用超时

**Type:** Edge Case
**需求来源:** REQ-REFUND-01（外部依赖）
**Preconditions:** order_id=100，状态=已支付(1)；`PaymentClient.call_refund` 超过 3s 无响应。

**Steps:**
1. 对 order_id=100 发起全额退款。
2. 第三方 3s 超时。

**Expected Result:** 触发重试（共 2 次）；仍失败则入补偿队列。 ……`src/clients/payment_client.py:55`

### TC-REFUND-09: 同一退款单幂等重放

**Type:** Edge Case
**需求来源:** REQ-REFUND-01（幂等）
**Preconditions:** order_id=100 已成功退款一次。

**Steps:**
1. 用相同退款单标识再次提交退款。

**Expected Result:** 命中 refund_records.order_id 唯一索引，识别为重复，不重复退款、不双扣。 ……`src/service/refund_service.py:160`
