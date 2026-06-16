# 测试用例文档模板

> 本 skill 的产出物之一。从已确认的 `analysis.md`（现状事实源）+ `requirements.md`（反推需求）派生**覆盖所有需求与边缘 case 的测试用例**。
> 用例格式与 `web-test-case-man` 对齐（自然语言结构化：`TC-<MODULE>-<n>` / Type / Preconditions / Steps / Expected Result），但**去掉对 FastAPI+Vue 栈的绑定**：不产出 Playwright 代码、不要 tech-design 输入、语言无关。
>
> **回链铁律**：每个用例的 Expected Result 都要回链 `file:line`（锚到 analysis 的真实代码行为），使它既是测试用例又是**行为规约**。覆盖规则见 `references/test-case-generation.md`。

---

## 一、模板

### frontmatter（轻量 YAML）

```yaml
---
business: order-refund            # 与同组 analysis / requirements 一致
title: 订单退款测试用例
analyzed_at: 2026-06-16
status: confirmed                 # draft / confirmed / example
source_analysis: 2026-06-16-order-refund-analysis.md       # ★ 现状事实源
source_requirements: 2026-06-16-order-refund-requirements.md  # ★ 反推需求（功能清单在此）
total_cases: <n>
by_type: {happy: <n>, error: <n>, edge: <n>}   # ★ 三类计数，须与正文实际用例一致
---
```

### 文档头（正文开头，紧跟 frontmatter）

```markdown
# <业务中文名> 测试用例

> 源自 analysis：`<source_analysis>` ／ 源自 requirements：`<source_requirements>`
> 生成日期：YYYY-MM-DD　用例总数：<n>（Happy <n> / Error <n> / Edge <n>）
```

### 模块节（一个 `##` 对应 requirements 的一个功能模块）

```markdown
## Module: <MODULE>（<中文模块名>）

> 覆盖 requirements §4 功能清单「<模块名>」模块。
```

### 用例格式（每个 `###` 一个用例）

````markdown
### TC-<MODULE>-<n>: <用例名（动作导向）>

**Type:** Happy Path | Error Flow | Edge Case
**需求来源:** REQ-<MODULE>-<n>（requirements §4 功能清单）   <!-- ★ 回链需求项 -->
**Preconditions:** <开始前必须为真的状态；无则写"无">

**Steps:**
1. <具体的、可观察的动作 / 系统条件>
2. <下一步>

**Expected Result:** <可观察、可断言的结果；负向用例须说明"什么没发生"> ……`路径:行号`
````

**命名约定**：
- `<MODULE>` = 模块名大写缩写（REFUND / ORDER / PAYMENT）。
- `<n>` = 模块内从 1 递增。
- 用例名 = 动作导向短句（"已支付订单全额退款"，不写"测试退款功能"）。

**覆盖要点**（详见 `references/test-case-generation.md`）：
- 每个 P0 功能 → ≥1 Happy + ≥1 Error + ≥1 Edge；每个 P1 → ≥1 Happy + ≥1 Edge。
- analysis 完整性 5 项（异常分支 / 触发条件 / 并发时序 / 外部依赖 / 幂等）每项至少有 1 个用例（多为 Edge Case 来源）。
- 每个 Expected Result 必须回链 `file:line`。
- **写实现行为而非 UI**（语言无关）：从"调接口/改了什么状态"角度写 Steps，不写"点击按钮"这类绑栈 UI。

---

## 二、端到端示例

> 示例：订单退款测试用例（与同组 `analysis.md` / `requirements.md` 配对，**代码路径为虚构示例**）。

```yaml
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
```

# 订单退款测试用例

> 源自 analysis：`2026-06-16-order-refund-analysis.md` ／ 源自 requirements：`2026-06-16-order-refund-requirements.md`
> 生成日期：2026-06-16　用例总数：9（Happy 2 / Error 3 / Edge 4）

## Module: REFUND（退款发起）

> 覆盖 requirements §4「退款发起」模块。

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
