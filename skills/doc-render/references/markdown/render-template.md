# Markdown 渲染规范：doc.md → 干净可读 Markdown

> 用途：把 `doc.md`（带意图标注）渲染成**最终 Markdown 成品**。Markdown 是 `doc.md` 的**机械投影**：不新增意图块、不改数字、不改内容。意图块解析为最终 MD 语法。
> 蓝本：上游 `doc-blueprint` 的 `preview.md` 是同源投影的草稿；本后端产出的是**可发布的成品**（解析更彻底：图表→mermaid、表格→对齐、标记保留供对账）。
> 组件结构见 `component-mapping.md`；标记契约见 `projection.manifest.yaml`。交付前必须跑 `scripts/audit_projection.py`。

---

## 一、硬性原则

1. **单一 `.md` 文件**：干净、可贴用、GitHub 风格 Markdown 友好。
2. **严格投影**：每个意图块对回 `doc.md` 的一条声明（figures / 正文块）；不发明块、不漏块、不改数字。
3. **数据同源**：`{{d:id}}` → `datasets[].value` + `unit`；不在成品里发明另一套数字。
4. **投影标记**：每个图表/KPI/timeline/callout/status/table-intent/diagram 块前发 `<!-- doc:proj id=.. kind=.. -->`（对账锚点，不显示）。

---

## 二、doc.md 元素 → Markdown 投影

| doc.md 元素 | Markdown 成品 | 要求 |
|-------------|--------------|------|
| front-matter | 删除 | 成品不含 front-matter（给人读） |
| `<!-- doc:section slot= -->` | 删除注释，保留标题 | 章节标题照搬 |
| `{{d:id}}` | `value unit` | 从 datasets 解析 |
| `[ref:id]` | `[label](url)` | 从 references 解析 |
| ` ```chart ``` ` | ` ```mermaid ``` `（xychart/pie） | 见 component-mapping §chart |
| ` ```kpi ``` ` | 引用块 + 大数字 | 见 component-mapping §kpi |
| ` ```timeline ``` ` | Markdown 表格 | 见 component-mapping §timeline |
| ` ```mermaid ``` ` | 原样保留 | 原生 mermaid |
| `> [!variant]` | 原样保留（admonition） | GitHub 风格，多数 MD 渲染器支持 |
| `[badge:L text]` | `emoji text`（绿🟢/黄🟡/红🔴/橙🟠/✅/⚪） | 全文首次处保留图例 |
| 原生表格 | 保留（必要时补对齐 `:--`） | 表格意图注释删除 |
| 原生列表/代码 | 原样保留 | — |

---

## 三、解析流程（机械投影）

1. 读 `doc.md`，解析 front-matter 得 `datasets`/`figures`/`references`。
2. 删除 front-matter 块。
3. 逐行扫描正文：
   - 删除 `<!-- doc:section ... -->` 注释。
   - `{{d:id}}` → datasets 插值（value + 空格 + unit；unit 为"无"则只 value）。
   - `[ref:id]` → `[label](url)`；未匹配的 ref 保留原文并记入未决。
   - fenced `chart`/`kpi`/`timeline` 块 → 按 component-mapping 替换，前置 `<!-- doc:proj ... -->`。
   - fenced `mermaid` → 前置 `<!-- doc:proj id=<title> kind=diagram -->`，保留内容。
   - `[badge:L text]` → `emoji text`。
   - 表格前的 `<!-- doc:intent=... -->` → 替换为 `<!-- doc:proj id=<slot|n> kind=table -->`（保留对账），删除 intent 文本。
   - admonition 前置 `<!-- doc:proj id=<variant-n> kind=callout -->`，原样保留。
4. 写出 `<主题>.md`。

---

## 四、投影标记（对账锚点，不可删）

```
<!-- doc:proj id=impact_by_minute kind=chart:bar -->
<!-- doc:proj id=kpi_impact kind=kpi -->
<!-- doc:proj id=tl kind=timeline -->
<!-- doc:proj id=decision-1 kind=callout -->
<!-- doc:proj id=status-1 kind=status -->
<!-- doc:proj id=matrix kind=table -->
<!-- doc:proj id=arch kind=diagram -->
```

> Markdown 可有视觉优化，但**不得删除这些标记**（HTML 注释不显示，不影响阅读）。

---

## 五、交付前对账

```bash
python skills/doc-render/scripts/audit_projection.py <doc.md> <render-dir> --backend markdown
```

重点：`doc.md` 声明的每个 figures/正文块（id+kind）在成品里都有对应 `doc:proj` 标记；成品无 `doc.md` 未声明的块；`{{d:}}` 无残留占位。
