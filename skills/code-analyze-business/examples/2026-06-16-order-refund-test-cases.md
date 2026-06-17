---
business: order-refund
title: 订单退款测试用例
analyzed_at: 2026-06-16
status: example
source_analysis: 2026-06-16-order-refund-analysis.md
source_requirements: 2026-06-16-order-refund-requirements.md
total_cases: 12
by_type: {happy: 3, error: 3, edge: 6}
---

# 订单退款测试用例

> 源自 analysis：`2026-06-16-order-refund-analysis.md` ／ 源自 requirements：`2026-06-16-order-refund-requirements.md`
> 生成日期：2026-06-16　用例总数：12（Happy 3 / Error 3 / Edge 6）
> Expected Result 用业务可观察断言（黑盒），file:line 归独立「实现锚点」行。需求来源指向 requirements §4 的 REQ id。

## Module: REFUND（退款发起）

> 覆盖 requirements §4「退款发起」「可靠性」模块。

### TC-REFUND-01: 已支付订单全额退款

**Type:** Happy Path
**需求来源:** REQ-REFUND-01
**Preconditions:** 存在一笔已支付订单，金额 100，未发起过退款。

**Steps:**
1. 对该订单发起全额退款（退款金额 = 100）。

**Expected Result:** 退款成功，订单变为"已退款"，退款金额原路退回；退款单记录为成功。
**实现锚点:** `src/repo/order_repo.py:120`

### TC-REFUND-02: 已支付订单部分退款

**Type:** Happy Path
**需求来源:** REQ-REFUND-03
**Preconditions:** 一笔已支付订单，金额 100。

**Steps:**
1. 对该订单发起部分退款（退款金额 = 30）。

**Expected Result:** 部分退款 30 成功，订单仍为"已支付"（可退余额变为 70），退款单记录金额 30。
**实现锚点:** `src/service/refund_service.py:110`

### TC-REFUND-03: 已退款订单再次退款

**Type:** Error Flow
**需求来源:** REQ-REFUND-02
**Preconditions:** 一笔订单已为"已退款"。

**Steps:**
1. 对该订单再次发起退款。

**Expected Result:** 退款申请被拒绝并提示"不可退"，订单状态保持"已退款"不变。
**实现锚点:** `src/service/refund_service.py:97`

### TC-REFUND-04: 退款金额超过可退余额

**Type:** Error Flow
**需求来源:** REQ-REFUND-03
**Preconditions:** 一笔已支付订单，金额 100，已部分退款 30（可退余额 = 70）。

**Steps:**
1. 对该订单发起退款（退款金额 = 80，> 可退余额 70）。

**Expected Result:** 退款申请被拒绝并提示"超过可退余额"；不发起真实退款、不创建退款单。
**实现锚点:** `src/service/refund_service.py:112`

### TC-REFUND-05: 第三方支付退款失败

**Type:** Error Flow
**需求来源:** REQ-REFUND-07
**Preconditions:** 一笔已支付订单；支付系统本次退款返回失败。

**Steps:**
1. 对该订单发起全额退款。
2. 支付系统连续重试仍失败。

**Expected Result:** 退款被记为失败并由系统兜底重试，用户不直接收到报错；订单保持"已支付"。
**实现锚点:** `src/service/refund_service.py:138`

### TC-REFUND-06: 退款请求参数缺失

**Type:** Edge Case
**需求来源:** REQ-REFUND-01
**Preconditions:** 无。

**Steps:**
1. 对某订单发起退款但未提供退款金额。

**Expected Result:** 请求被参数校验拦截并提示"参数错误"，不进入退款业务逻辑。
**实现锚点:** `src/api/refund.py:44`

### TC-REFUND-07: 同一订单并发双退

**Type:** Edge Case
**需求来源:** REQ-REFUND-06（幂等）
**Preconditions:** 一笔已支付订单；两个全额退款请求同时到达。

**Steps:**
1. 并发发起两次全额退款（同一订单）。

**Expected Result:** 只有一次退款成功，另一次被拒绝（识别为重复），不发生重复退款。
**实现锚点:** `src/service/refund_service.py:160`

### TC-REFUND-08: 第三方退款调用超时

**Type:** Edge Case
**需求来源:** REQ-REFUND-04（外部依赖）
**Preconditions:** 一笔已支付订单；支付系统超过超时阈值仍无响应。

**Steps:**
1. 对该订单发起全额退款。
2. 支付系统超时无响应。

**Expected Result:** 系统自动重试；仍失败则转入兜底重试，不向用户直接报错。
**实现锚点:** `src/clients/payment_client.py:55`

### TC-REFUND-09: 同一退款单幂等重放

**Type:** Edge Case
**需求来源:** REQ-REFUND-06（幂等）
**Preconditions:** 该订单已成功退款一次。

**Steps:**
1. 用相同退款标识再次提交退款。

**Expected Result:** 系统识别为重复退款，不再发起真实退款、不重复扣款。
**实现锚点:** `src/service/refund_service.py:160`

### TC-REFUND-10: 退款成功后订单状态正确更新

**Type:** Happy Path
**需求来源:** REQ-REFUND-05
**Preconditions:** 一笔已支付订单，退款金额合法；支付系统返回成功。

**Steps:**
1. 对该订单发起全额退款，支付系统返回成功。

**Expected Result:** 退款成功后，订单由"已支付"变为"已退款"，资金原路退回。
**实现锚点:** `src/repo/order_repo.py:120`

### TC-REFUND-11: 一笔订单分多次部分退款

**Type:** Edge Case
**需求来源:** REQ-REFUND-08
**Preconditions:** 一笔已支付订单，金额 100。

**Steps:**
1. 先对该订单部分退款 30（成功）。
2. 再次部分退款 40（成功）。
3. 第三次部分退款 40（累计 110 > 订单金额 100）。

**Expected Result:** 规则未明确 ⚠ 未确认；按当前实现前两次部分退款成功、可退余额递减，第三次超过可退余额应被拒绝。是否支持一笔订单分多次部分退需找产品确认。
**实现锚点:** `src/service/refund_service.py:110`

### TC-REFUND-12: 第三方持续失败至补偿重试上限

**Type:** Edge Case
**需求来源:** REQ-REFUND-09（外部依赖）
**Preconditions:** 一笔已支付订单；支付系统持续返回失败。

**Steps:**
1. 对该订单发起全额退款。
2. 支付系统持续失败，补偿 job 重试至上限。

**Expected Result:** 重试上限与放弃条件不在本业务内 ⚠ 未确认；按当前实现退款单记录失败并由外部 job 兜底，订单保持"已支付"，用户不直接收到报错。
**实现锚点:** `src/service/refund_service.py:138`
