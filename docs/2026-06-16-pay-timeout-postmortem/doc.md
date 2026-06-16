---
doc:
  id: pay_timeout_postmortem
  title: 6/14 支付超时事故复盘
  doc_type: postmortem
  intent: 让支付团队与 SRE 认领改进项并在两周内落地
  audience:
    primary: 支付后端负责人、SRE 值班
    secondary: 技术总监
  desired_action: 相关人当场认领 Action，两周内完成修复并验收
  tone: internal
  length: standard
sources:
  brief: docs/2026-06-14-pay-timeout-brief.md
  confirmed_by_user: true
  question: 是否需要参考已有事故记录或监控数据？
  items:
    - id: pay_alert
      path: 支付中台 6/14 告警
      type: data
      role: source_of_truth
      freshness: current
      decision: adopted
      note: 影响数字与时间线的唯一事实源
datasets:
  - { id: affected_orders, value: 1284, unit: 单, caliber: "6/14 00:00–02:30 支付超时失败订单", source: 支付中台告警, confidence: measured }
  - { id: duration_min, value: 150, unit: 分钟, caliber: 首个告警到完全恢复, source: 值班记录, confidence: measured }
  - { id: peak_concurrency, value: 3200, unit: 并发, caliber: 峰值并发请求数, source: 网关监控, confidence: measured }
  - { id: revenue_loss, value: 38, unit: 万元, caliber: 失败订单潜在营收（估算）, source: 财务估算, confidence: estimated }
  - { id: pool_limit, value: 50, unit: 连接, caliber: 连接池配置上限, source: 配置中心, confidence: measured }
figures:
  - { id: impact_by_minute, kind: "chart:bar", title: 超时量/分钟, data_ref: inline, note: 内嵌示意 }
references:
  - { id: r1, label: 连接池监控定义, url: "confluence://OBS/pay-pool" }
---

# 6/14 支付超时事故复盘

<!-- doc:section slot=summary intent=一句话说清发生了什么与当前状态 -->
## 摘要
6/14 00:00 起，支付核心连接池被打满，导致支付请求大面积超时，持续 {{d:duration_min}} 分钟，影响 {{d:affected_orders}} 单订单。当前状态：[badge:healthy 已恢复]。严重程度 P1。

> [!warning] 图例：状态颜色含义
> 🟢 已恢复 / 🟡 降级运行 / 🔴 故障中

<!-- doc:section slot=impact intent=量化事故影响 -->
## 影响
本次事故影响 {{d:affected_orders}} 单支付订单，持续 {{d:duration_min}} 分钟，估算资损 {{d:revenue_loss}}（口径见 datasets）。严重程度定级 P1。

```chart kind=bar id=impact_by_minute data_ref=inline title="超时量/分钟（示意）"
```

<!-- doc:section slot=timeline intent=从告警到恢复的关键节点 -->
## 时间线

```timeline
- 00:00  告警：支付超时率突增
- 00:08  值班介入，定位连接池打满（使用率 {{d:pool_limit}} 配置）
- 01:30  扩容 + 限流，超时率回落
- 02:30  完全恢复
```

<!-- doc:section slot=root_cause intent=论证系统性根因 -->
## 根因
直接原因：流量峰值并发达 {{d:peak_concurrency}}，连接池上限 {{d:pool_limit}} 被打满，请求排队 → 超时级联 → 用户支付失败[ref:r1]。
系统性根因：① 缺少自动限流，峰值流量直达下游；② 连接池容量未随流量弹性扩缩；③ 监控仅有"使用率"，无"即将打满"的提前告警。

<!-- doc:section slot=actions intent=可追责可验收的改进项 -->
## 改进项
| Action | Owner | DDL | 验收 |
|--------|-------|-----|------|
| 接入自适应限流 | 张三 | 6/28 | 峰值并发>阈值时限流生效，超时率<0.1% |
| 连接池弹性扩缩 | 李四 | 7/05 | 压测并发 2x 不打满 |
| 增加提前告警 | 王五 | 6/20 | 使用率>80% 提前 5 分钟告警 |

> [!decision] 限流算法选令牌桶
> 理由：需支持突发流量且可平滑限速。备选：漏桶（不支持突发，否）；计数器（粗粒度，否）。

<!-- doc:section slot=lessons intent=可复用的经验沉淀 -->
## 经验沉淀
- 应急动作："限流 + 扩容"组合可在 30 分钟内止血，写入值班手册。
- 监控补齐方向：所有连接池类资源加"使用率>80% 提前告警"。

## 校验报告

```bash
python skills/doc-blueprint/scripts/validate_doc.py docs/2026-06-16-pay-timeout-postmortem/doc.md
```

（见运行结果）

## 未决问题
- 资损精确金额：财务次日给出，先用 {{d:revenue_loss}} 区间占位（estimated）。
