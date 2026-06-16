# 输出格式：doc.md + preview.md

> 配合 Checklist 第 9 步。交付目录必须同时包含 `doc.md`、`preview.md`。可选保存 `doc.meta.json`，方便脚本稳定读取。

---

## 一、交付目录

```text
docs/YYYY-MM-DD-<主题>/
├── doc.md            # 带意图标注的蓝图规范（单一事实源）
├── preview.md        # 草预览：doc.md 的机械投影，纯净可读 Markdown
└── doc.meta.json     # 可选：front-matter 抽取
```

---

## 二、`doc.md` 固定模板

````markdown
---
doc:
  id: <snake_case>
  title: <标题>
  doc_type: <postmortem | rfc | prd | adr | business_case | runbook | weekly | changelog | announcement | meeting | article | custom>
  intent: <一句话：让谁读完做什么>
  audience:
    primary: <主要读者>
    secondary: <次要读者 | null>
  desired_action: <可判定的读者动作>
  tone: <formal | internal | external | technical>
  length: <short | standard | long>
sources:
  brief: <brief 路径 | user_prompt>
  confirmed_by_user: true
  question: <向用户确认参考源时的问题>
  items:
    - id: <snake_case>
      path: <路径或来源>
      type: <brief | doc | code | data | spec | user_prompt | other>
      role: <source_of_truth | context_only | stale_or_conflicting>
      freshness: <current | unknown | stale>
      decision: <adopted | used_for_context | ignored>
      note: <理由>
datasets:
  - id: <snake_case>
    value: <number|string>
    unit: <单位>
    caliber: <口径/时点/范围>
    source: <来源>
    confidence: <measured | estimated | assumed>
figures:
  - id: <snake_case>
    kind: <chart:bar | chart:line | chart:pie | diagram | kpi | timeline>
    title: <标题>
    data_ref: <dataset_id | [dataset_id] | inline>
    note: <可选>
references:
  - id: <r1>
    label: <来源标签>
    url: <链接 | confluence:// | path>
---

# <标题>

<!-- doc:section slot=<必备章节1> intent=<该章为何存在> -->
## <章节1>
正文……数字用 {{d:<id>}} 插值；论断带证据 [ref:<id>]。

> [!decision] <决策>
> 理由：<…>。备选：<…>，不选因为 <…>。

```chart kind=bar id=<fig_id> data_ref=<dataset_id> title="<图表标题>"
```

<!-- doc:section slot=<必备章节2> intent=<…> -->
## <章节2>
……

## 校验报告

```bash
python skills/doc-blueprint/scripts/validate_doc.py docs/YYYY-MM-DD-<主题>/doc.md
```

记录 ERROR/WARNING 结果、质量分、修复记录。

## 未决问题

只记录正文范围外或意图待确认事项。
````

---

## 三、`preview.md`（草预览投影规则）

按 `markdown-annotated.md` §三 机械投影：

````markdown
# <标题>

## <章节1>
正文……（{{d:id}} 已解析为"值 单位"，[ref:id] 解析为链接）。

> 决策：<决策>
> 理由：<…>。备选：<…>。

> 📊 图：<图表标题>（柱状 · 数据见 datasets.<id>）

> [!warning] <警示标题>
> <内容>

## <章节2>
……
````

> preview 删除 front-matter 与所有 `<!-- doc:... -->` 注释；图表/KPI/timeline 块替换为引用块占位；`[badge:L text]` → `emoji text`；mermaid 原样保留。每个占位/状态/数字都能对回 `doc.md` 的一条声明。

---

## 四、`doc.meta.json`（可选，脚本用）

front-matter 的 JSON 抽取，供 `validate_doc.py` / `doc-render` 稳定读取（避免重复解析 YAML）：

```json
{
  "doc": { "id": "...", "doc_type": "postmortem", "desired_action": "...", "audience": {"primary":"..."} },
  "datasets": [ {"id":"affected_orders","value":1284,"unit":"单","caliber":"...","source":"...","confidence":"measured"} ],
  "figures":   [ {"id":"impact_by_minute","kind":"chart:bar","data_ref":"per_minute"} ],
  "sources":   { "brief":"docs/...-brief.md", "confirmed_by_user": true, "items": [] }
}
```

> `doc.md` 的 front-matter 与 `doc.meta.json` 必须一致；以 `doc.md` 为单一事实源，meta 是其抽取。
