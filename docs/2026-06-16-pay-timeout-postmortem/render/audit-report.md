# 渲染对账报告 · 6/14 支付超时事故复盘

> 输入：`../doc.md`（已通过 `validate_doc.py`）。
> 命令：
> ```bash
> python skills/doc-blueprint/scripts/validate_doc.py ../doc.md
> python skills/doc-render/scripts/audit_projection.py ../doc.md .. --backend all
> ```

## 输入门禁
- `validate_doc.py`：ERROR 0 / WARNING 0 / 质量分 100% —— **通过**。

## 声明块
- `impact_by_minute` → `chart:bar`（来自 `figures[]` + 正文 chart 块）

## 逐后端对账结果

### Markdown（`markdown/pay-timeout-postmortem.md`）
- 🔴 ERROR 0　🟡 WARNING 0
- 声明块 `impact_by_minute:chart:bar` 已投影（mermaid xychart-bar）。
- 行内元素投影标记（callout/timeline/table）—— ℹ️ 正常。
- `{{d:}}` 全部解析（无残留）。

### Confluence（`confluence/pay-timeout-postmortem.confluence.xhtml`）
- 🔴 ERROR 0　🟡 WARNING 0
- 声明块 `impact_by_minute:chart:bar` 已投影（`ac:structured-macro ac:name="chart"`，type=bar + 内嵌数据表）。
- callout→info/warning 宏、status→status 宏、timeline/table→原生表 —— ℹ️ 正常。
- `{{d:}}` 全部解析（无残留）。

## 结论
两后端对账通过（总 ERROR 0）。成品可发布：
- Markdown：直接贴用 / 存 Wiki。
- Confluence：存储格式正文，粘进 Confluence「插入 → 存储格式」。
