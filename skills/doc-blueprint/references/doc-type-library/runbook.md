# 操作指引 / SOP（runbook）

## 匹配信号
日常运维/应急操作指引。读者动作：**照着做就能正确执行**。强调"可操作、可回滚、可升级"。

## 必备章节（slot）与每节必含

| slot | 标题示例 | 每节必含 |
|------|----------|----------|
| `trigger` | 触发条件 | 什么情况用这份（告警/现象/阈值），怎么判断 |
| `precheck` | 前置检查 | 动手前确认的事项、权限、依赖 |
| `steps` | 操作步骤 | **分步 + 可复制命令**（`code` 块）；每步预期结果 |
| `expected` | 预期结果 | 每步/整体成功长什么样 |
| `rollback` | 回滚步骤 | 做错了怎么退回（**必备**，不能只进不退） |
| `escalation` | 升级路径 | 搞不定找谁、何时升级 |

> `rollback` 是 Runbook 的安全带：只写"怎么做"不写"怎么退"的操作文档是隐患。

## 常见缺陷
- 步骤只有描述没有可复制命令（要人手敲易错）。
- 没有 `rollback`（出事无法回退）。
- 没有 `trigger`（不知道何时该用）。
- 缺预期结果（操作者不知道做到没）。
- 命令带占位参数却不说明填什么。

## 专业示例片段
````markdown
<!-- doc:section slot=trigger intent=何时用这份 -->
## 触发条件
监控告警"支付连接池使用率>95% 持续 3 分钟"时执行。

<!-- doc:section slot=steps intent=可复制命令的分步操作 -->
## 操作步骤
1. 确认当前连接池使用率：
   ```bash
   kubectl -n pay exec deploy/pay-core -- curl -s localhost:9090/metrics | grep pool_usage
   ```
   预期：输出 `pool_usage 0.97` 量级。
2. 触发限流阀值上调（应急）：
   ```bash
   kubectl -n pay set env deploy/pay-core LIMIT_QPS=2000
   ```
   预期：30s 内使用率回落到 <80%。

<!-- doc:section slot=rollback intent=做错怎么退 -->
## 回滚
若上调后下游报错激增，恢复原值：
   ```bash
   kubectl -n pay set env deploy/pay-core LIMIT_QPS=1000
   ```
````
