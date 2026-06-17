# 链路覆盖策略：5 个 pass + LSP/rg 双轨取证

> 配合 `code-analyze-business` 的 Checklist 第 4 步使用。前提：业务范围已由用户确认（第 3 步通过）。这一步解决**"该找的都找全了吗"**——`tracing-flow.md` 教你怎么把一条主链路追透，本文件教你怎么**保证没有遗漏的入口、旁路、数据副作用与横切逻辑**。两者互补：`tracing-flow` 是"找透"，本文件是"找全"。

## 一、为什么需要"找全"而不仅是"追透"

只从确认的那个入口自顶向下追一条链路，是这类分析最常见的失真来源：

- **漏入口**：退款主流程你跟的是 `POST /api/refund`，但同一个退款 `RefundService.refund` 可能还被一个**定时任务**（`refund-sync-job`）或一条 **MQ 消息**（客服后台触发）调用——只跟接口就漏了旁路。
- **漏反向引用**：核心 service 可能被多个 handler 共用；只追你确认的那一个 caller，看不到别的触发路径。
- **漏数据副作用**：状态字段 / cache key / event name 可能在别处被读写，"只追调用链"看不到这些隐式副作用。
- **漏横切逻辑**：权限校验、事务边界、分布式锁、重试策略、feature flag 往往不在主链路的方法体里，而是拦截器 / 装饰器 / 中间件 / 配置——追调用链追不到。

**对策**：硬性做 **5 个 pass**，每个 pass 给「候选 / 发现 → 判定 → 回链」，结果收进 `analysis.md` 的「链路覆盖（5-pass）」节。校验脚本 `validate_analysis.py` 的 **R-L4** 硬卡这 5 项齐全。

## 二、5 个 pass（硬性，逐 pass 取证）

每个 pass 的产出统一为三分法：**纳入链路**（确认属于本业务，进主流程/矩阵）/ **排除**（确认不属于，写明原因）/ **待确认旁路**（疑似但未证实，标 `⚠ 未确认` 并登记「已知缺口」）。

### Pass 1 · 入口覆盖

按**所有可能形态**搜入口，列「候选入口」清单，逐条标纳入 / 排除（排除必写"为什么不属于本业务"）。形态见 `locating-business.md §二`：

- HTTP：`@app.` / `@router.` / `@Controller` / `@GetMapping` / `router.post` / `@api_view`
- MQ：`@RabbitListener` / `@KafkaListener` / `consume` / `on_message` / `@EventHandler`
- 定时：`@Scheduled` / celery beat / `cron` / `APScheduler`
- 事件：`@EventListener` / `emit` / `publish` / `dispatch` / `on(`
- CLI / 手动：`def main(` / `if __name__` / `argparse` / `click.command`

> 候选入口不要只列你"已经知道"的那个——要主动**按这 5 类去搜**，把搜到的都列进候选，再逐条判定。这一步拦住"漏掉定时/MQ/事件旁路入口"。

### Pass 2 · 调用链覆盖

从**确认入口**向下追到**外部边界**（DB 写入 / 外部 HTTP / 消息发出 / 返回响应），记录**每一条分支 + 每一个早返回**，不止 happy path。逐项见 `tracing-flow.md §一`（异常 / 兜底 / 兼容 / 异步 / 重试）。

> "追到外部边界"是硬停止点——到了 DB / 外部调用 / 消息发出 / 返回响应就停，不展开通用工具函数。

### Pass 3 · 反向引用覆盖

对**核心 service / function / event / topic** 查 **caller**（谁调用了它），确认是否存在其他触发路径（旁路入口）。这是反漏"共用 service 的隐藏 caller"。

- 查 `RefundService.refund` 的 caller：除了 `/api/refund`，有没有定时 job / MQ handler / 别的接口也调它？
- 查本业务发出的事件 / topic 的**订阅者**：有没有别的链路因此被触发（是否应纳入"影响面"）？

> 反向引用最容易用 LSP 的 `incomingCalls` / `findReferences` 精确拿到（见 §三）。无 LSP 时用 rg 搜符号名降级。

### Pass 4 · 数据副作用覆盖

对**关键实体 / 状态字段 / 表 / cache key / event name** 搜**所有读写点**，与 `analysis §6` 的字段字典呼应：

- 实体字段：`orders.status` 在哪些地方被读 / 被改？
- cache key：`refund_lock:{order_id}` 在哪 set / del / expire？
- event name：本业务发出的事件，谁发、谁订阅？

> 数据副作用是"追调用链"看不到的隐式耦合——状态字段的额外赋值点往往是 bug 温床。

### Pass 5 · 横切逻辑覆盖

检查**不在主链路方法体里**的横切关注点：权限 / 拦截器 / 中间件 / 事务 / 锁 / 配置 / feature flag / 重试策略。

- 权限：本业务入口有没有鉴权拦截器？匿名能不能调？
- 事务：哪些写操作在一个事务里？事务边界在哪？
- 锁：并发控制用分布式锁 / 唯一索引 / 乐观锁？key 是什么？
- 重试：外部调用失败重试几次、退避策略？
- 配置 / feature flag：有没有开关让本行为在部分环境不一样？

> 没有的显式标"不适用"，但得**逐项过一遍**——横切逻辑漏掉是线上事故的高发区。

## 三、LSP / 符号索引：先检测、有则用足、无则降级

符号覆盖优先用 LSP（精确），没有则降级 rg 文本搜索。**协议如下，严格按序**：

1. **先检测**：对入口文件做一次廉价 LSP 探测（如 `documentSymbol` on 入口 handler 文件）。
   - 返回结果 → **LSP 可用**，走 §四 的 5 个符号查询。
   - 报错（无 language server / server 未就绪 / 不支持该语言）→ **LSP 不可用**，走第 3 步降级。

2. **可用时用足**（见 §四）：对入口 handler、核心 service、接口 / 抽象类、关键实体 / 枚举 / 字段分别用对应 LSP 操作取证。

3. **不可用时不主动安装**：根据代码语言，**在对话里**（interactive，**绝不写进 `analysis.md` 等产出文档**）给用户一句安装建议（如"装 Pyright 即可用 LSP 精确查 Python 符号引用"），然后**等用户回复**：
   - 回复"装好了" → 回到第 1 步重试探测；
   - 回复"跳过 LSP" → 用第 4 步 rg 降级。
   - **得到回复前不继续深挖。**

4. **降级**：无 LSP 时用 `rg` 搜函数名 / 类名 / 路由 / topic / 状态枚举 / 表字段。在「链路覆盖」节**标注「LSP unavailable，符号覆盖为文本搜索降级」**（这一标注写进文档；安装建议不写进文档）。

> 原则：能用精确符号查询就用，但**不为分析自作主张去装工具**——装不装是用户的环境决策，由用户拍板。

## 四、LSP 可用时的 5 个符号查询

检测到 LSP 可用后，按下表取证，把结果分「纳入链路 / 排除原因 / 待确认旁路」：

| # | 目标 | LSP 操作 | 拿到什么 |
|---|------|----------|----------|
| 1 | 入口 handler | `incomingCalls` / `findReferences` | 谁触发本入口（路由注册、调度注册、消息订阅） |
| 2 | 核心 service / function | `incomingCalls` + `outgoingCalls` | 谁调用它（旁路 caller）+ 它调了谁（下游） |
| 3 | 接口 / 抽象类 | `goToImplementation` / `implementations` | 有几个实现、主流程走哪个实现 |
| 4 | 关键实体 / 状态枚举 / 字段 | `findReferences` | 所有读写 / 赋值点（呼应 Pass 4 数据副作用） |
| 5 | （合成）全部命中 | —— | 归类：纳入链路 / 排除原因 / 待确认旁路 |

> 无 LSP 时把每一行换成"rg 搜符号名 → 人工判定调用关系"，并在节首标注降级。

## 五、结果落地到 analysis「链路覆盖（5-pass）」节

5 个 pass 的产出收进 `analysis.md` 的一张表（模板见 `analysis-template.md`），逐行「Pass | 候选/发现 | 判定 | 依据/锚点」。校验脚本 R-L4 硬卡 5 项齐全且每项有判定（纳入 / 排除 / 待确认 / 不适用）。

示例（退款业务，节选）：

| Pass | 候选 / 发现 | 判定 | 依据 / 锚点 |
|------|-----------|------|------------|
| 入口覆盖 | HTTP `POST /api/refund`；定时 `refund-sync-job` | 纳入：`/api/refund`；排除：`refund-sync-job`（只同步第三方退款状态，不发起新退款） | `src/api/refund.py:42` |
| 调用链覆盖 | `refund` → service → payment → repo，3 个早返回 | 纳入：全链路 + 状态/金额/可退 3 个早返回 | `src/service/refund_service.py:88` |
| 反向引用覆盖 | `RefundService.refund` 的 caller（LSP incomingCalls） | 纳入：仅 `/api/refund` 触发，无旁路 | `src/api/refund.py:42` |
| 数据副作用覆盖 | `orders.status`、`refund_records`、Redis `refund_lock:{order_id}` | 纳入：orders.status / refund_records 写点；refund_lock 见横切 | `src/repo/order_repo.py:120` |
| 横切逻辑覆盖 | 鉴权、事务、`refund_lock`、重试 2 次 | 纳入：refund_lock + 事务 + 重试 2 次；不适用：feature flag | `src/service/refund_service.py:160` |

## 六、防臆造（与 `quality-rules.md §一` 一致）

- 每个判定都要能回链 `file:line`；查不到依据的旁路标 `⚠ 未确认` 并登记「已知缺口」，不混进"纳入"当事实。
- LSP / rg 的命中**只作为线索**——是否真属于本业务链路，仍要看代码确认（注释可能过时，以代码为准）。
- 排除项必须写清"为什么不属于本业务"，不能只标"排除"。
