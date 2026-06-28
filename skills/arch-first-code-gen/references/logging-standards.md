# 按栈日志规范（模块 C / 日志门）

> 配合 `arch-first-code-gen` 的 Checklist 第 5 步。日志要「清晰规范」：**级别正确、结构化、关键节点打点、错误带上下文、用对按栈日志库**（PRD §4-C P0）。日志门（模块 E）按栈关键字结构性检查覆盖。

## 一、日志级别（用对）

| 级别 | 何时用 |
|---|---|
| **ERROR** | 影响业务结果/需人工介入的异常；**必须带入参 + 堆栈 + 上下文** |
| **WARN** | 可降级/可恢复的异常、业务告警（如库存低、限流触发） |
| **INFO** | 关键业务节点（入口/出口/外部调用/状态变更）——给运维与排查用 |
| **DEBUG** | 细节诊断；默认关闭，按需开 |

> **反模式**：吞异常只 `log.error(e.getMessage())` 不带堆栈；正常流程用 ERROR；DEBUG 常开刷屏。

## 二、结构化 + 关键节点打点

- **结构化**：关键字段成对（如 `log.info("createOrder userId={} amount={}", uid, amt)`），便于检索；避免把整个对象 `toString` 塞进去。
- **关键节点必打**：
  - **入口**：请求/用例开始（带关键入参，**不含敏感信息**）。
  - **出口**：用例完成（带结果概要/耗时）。
  - **异常**：catch 处带上下文 + 堆栈。
  - **外部调用**：调 DB/MQ/第三方前后（带目标 + 耗时 + 结果）。
- **不打敏感信息**：密码、token、身份证、完整卡号等脱敏或不打。

## 三、按栈日志库（用对）

| 栈 | 日志库 | 典型写法 |
|---|---|---|
| **JVM**(Java/Kotlin) | SLF4J 接口 + Logback 实现 | `private static final Logger log = LoggerFactory.getLogger(Xxx.class);` `log.info("...{}", arg)` |
| **C++** | spdlog | `spdlog::info("... {}", arg);` `spdlog::error("... {}", arg);` |
| **FastAPI/Python** | `logging` 或 `loguru` | `logger.info("...", extra={...})` / `logger.info("... {}", arg)` |

> 日志门（`validate_gate.py`）按栈匹配关键字（JVM: `log.`/`logger.`/`LOGGER.`；C++: `spdlog::`；Python: `logger.`/`log.`）统计覆盖：每个代码单元应有关键节点日志；缺日志会按比例告警。

## 四、错误日志带上下文（PRD §4-C 验收）

ERROR 必须带入参 + 堆栈 + 业务上下文：

- JVM：`log.error("createOrder 失败 userId={} req={}", uid, req, e);`（SLF4J 最后一个参是 `Throwable` 自动打堆栈）。
- C++：`spdlog::error("createOrder 失败 userId={} what={}", uid, e.what());`（C++ 异常无自动堆栈，至少带 what + 关键入参）。
- Python：`logger.exception("createOrder 失败 userId=%s", uid)`（`exception` 自带堆栈）。

## 五、反模式

| 反模式 | 正确做法 |
|---|---|
| 吞异常 / 只打 message 不带堆栈 | ERROR 带入参 + 堆栈 + 上下文 |
| 关键节点不打点（入口/出口/外部调用无日志） | 关键节点必打 |
| 打敏感信息（密码/token/完整卡号） | 脱敏或不打 |
| 正常流程用 ERROR / DEBUG 常开 | 级别用对 |
| 日志散落各处风格不一 | 按栈统一日志库 + 结构化 |
| 把大对象 toString 塞日志 | 结构化关键字段 |
