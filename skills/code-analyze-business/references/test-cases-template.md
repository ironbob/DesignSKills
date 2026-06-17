# 测试用例文档模板

> 本 skill 的产出物之一。从已确认的 `analysis.md`（现状事实源）+ `requirements.md`（反推需求）派生**覆盖所有需求与边缘 case 的测试用例**。
> 用例格式与 `web-test-case-man` 对齐（自然语言结构化：`TC-<MODULE>-<n>` / Type / Preconditions / Steps / Expected Result），但**去掉对 FastAPI+Vue 栈的绑定**：不产出 Playwright 代码、不要 tech-design 输入、语言无关。
>
> **分层铁律**：Expected Result 用**业务可观察断言**（测试人员黑盒能验的），代码事实（file:line）放独立「实现锚点」行 —— 使它既是用例又是**行为规约**，但断言本身不写表名/状态码/异常类名。覆盖规则见 `references/test-case-generation.md`。

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
**需求来源:** REQ-<MODULE>-<n>   <!-- ★ 回链 requirements §4 的「具体功能」REQ id（不是模块级）；这是覆盖校验的 join key，必须真实存在 -->
**Preconditions:** <开始前必须为真的业务状态；无则写"无">

**Steps:**
1. <业务动作 + 具体测试数据；语言无关、不绑 UI>
2. <下一步>

**Expected Result:** <业务可观察断言：用户/系统层面看到什么；负向用例须说明"什么没发生"。不写表名/状态码/异常类名>
**实现锚点:** `路径:行号`   <!-- ★ 回链代码行为，使用例同时是行为规约 -->
````

**命名约定**：
- `<MODULE>` = 模块名大写缩写（REFUND / ORDER / PAYMENT）。
- `<n>` = 模块内从 1 递增。
- 用例名 = 动作导向短句（"已支付订单全额退款"，不写"测试退款功能"）。

**覆盖要点**（详见 `references/test-case-generation.md`；机器校验见 `<biz>-test-cases.json` + `validate_contract.py`）：
- **每个功能（P0/P1/P2）至少 1 个用例**（孤儿功能 = ERROR）；**Happy/Error/Edge 三类各 ≥1**（ERROR）。
- **每功能类型齐全**（P0 Happy+Error+Edge、P1 Happy+Edge）= WARNING 软提示（务实档：不逼迫为细碎功能硬造用例）。
- **analysis 完整性 5 项**（仅 analysis 标「有」的）每项 ≥1 用例（ERROR），通过 case 的 `covers` 字段登记。
- **Expected Result 用业务可观察语言**（黑盒）；代码事实（file:line）放独立「实现锚点」行，每个用例必填。
- **语言无关、不绑栈**：Steps 用业务动作 + 测试数据描述，不写"点击按钮"这类绑栈 UI。

> 除本 md 外，**同步产出 `<biz>-test-cases.json`**（机器校验的契约源）。它把用例结构化，使 `需求来源→REQ id`、覆盖、完整性可被精确校验（md 自由文本做不到）。md 用例与本 json 必须一致（`validate_test_cases_json.py` 会对账）。

#### test-cases.json 结构
```json
{
  "business": "<biz>",
  "source_analysis": "<同组 analysis>.md",
  "source_requirements": "<同组 requirements>.md",
  "total_cases": 0,
  "by_type": {"happy": 0, "error": 0, "edge": 0},
  "cases": [
    {"id": "TC-<MODULE>-01", "req": "REQ-<MODULE>-01",
     "type": "Happy|Error|Edge",
     "anchor": "<路径:行号>",
     "covers": ["exception", "trigger", "concurrency", "external", "idempotency"]}
  ]
}
```
> `req` 必须是 requirements.json 里真实存在的 feature id（`validate_contract.py XC-E1` 查）；`covers` 用规范 5 键（↔ 异常分支/触发条件/并发时序/外部依赖/幂等），无则空数组 `[]`。校验：`validate_test_cases_json.py <tc.json> [<tc.md>]`，跨文件契约 `validate_contract.py <req.json> <tc.json> [<analysis.md>]`。

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

> 覆盖 requirements §4「退款发起」「可靠性」模块。

### TC-REFUND-01: 已支付订单全额退款

**Type:** Happy Path
**需求来源:** REQ-REFUND-01（requirements §4）
**Preconditions:** 存在一笔已支付订单，金额 100，未发起过退款。

**Steps:**
1. 对该订单发起全额退款（退款金额 = 100）。

**Expected Result:** 退款成功，订单变为"已退款"，退款金额原路退回；退款单记录为成功。
**实现锚点:** `src/repo/order_repo.py:120`

### TC-REFUND-02: 已支付订单部分退款

**Type:** Happy Path
**需求来源:** REQ-REFUND-01
**Preconditions:** 一笔已支付订单，金额 100。

**Steps:**
1. 对该订单发起部分退款（退款金额 = 30）。

**Expected Result:** 部分退款 30 成功，订单仍为"已支付"（可退余额变为 70），退款单记录金额 30。
**实现锚点:** `src/service/refund_service.py:110`

### TC-REFUND-03: 已退款订单再次退款

**Type:** Error Flow
**需求来源:** REQ-REFUND-01
**Preconditions:** 一笔订单已为"已退款"。

**Steps:**
1. 对该订单再次发起退款。

**Expected Result:** 退款申请被拒绝并提示"不可退"，订单状态保持"已退款"不变。
**实现锚点:** `src/service/refund_service.py:97`

### TC-REFUND-04: 退款金额超过可退余额

**Type:** Error Flow
**需求来源:** REQ-REFUND-01
**Preconditions:** 一笔已支付订单，金额 100，已部分退款 30（可退余额 = 70）。

**Steps:**
1. 对该订单发起退款（退款金额 = 80，> 可退余额 70）。

**Expected Result:** 退款申请被拒绝并提示"超过可退余额"；不发起真实退款、不创建退款单。
**实现锚点:** `src/service/refund_service.py:112`

### TC-REFUND-05: 第三方支付退款失败

**Type:** Error Flow
**需求来源:** REQ-REFUND-01
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
**需求来源:** REQ-REFUND-01（幂等）
**Preconditions:** 一笔已支付订单；两个全额退款请求同时到达。

**Steps:**
1. 并发发起两次全额退款（同一订单）。

**Expected Result:** 只有一次退款成功，另一次被拒绝（识别为重复），不发生重复退款。
**实现锚点:** `src/service/refund_service.py:160`

### TC-REFUND-08: 第三方退款调用超时

**Type:** Edge Case
**需求来源:** REQ-REFUND-01（外部依赖）
**Preconditions:** 一笔已支付订单；支付系统超过超时阈值仍无响应。

**Steps:**
1. 对该订单发起全额退款。
2. 支付系统超时无响应。

**Expected Result:** 系统自动重试；仍失败则转入兜底重试，不向用户直接报错。
**实现锚点:** `src/clients/payment_client.py:55`

### TC-REFUND-09: 同一退款单幂等重放

**Type:** Edge Case
**需求来源:** REQ-REFUND-01（幂等）
**Preconditions:** 该订单已成功退款一次。

**Steps:**
1. 用相同退款标识再次提交退款。

**Expected Result:** 系统识别为重复退款，不再发起真实退款、不重复扣款。
**实现锚点:** `src/service/refund_service.py:160`
