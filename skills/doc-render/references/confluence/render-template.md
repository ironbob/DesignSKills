# Confluence 渲染规范：doc.md → 存储格式 XHTML

> 用途：把 `doc.md` 渲染成 **Confluence 存储格式（Storage Format, XHTML）** 成品，可直接粘进 Confluence「插入 → 存储格式 / Storage Format」。
> 成品是 `doc.md` 的**机械投影**：意图块映射到 Confluence 原生宏（`ac:structured-macro`），数字同源 datasets。
> 组件结构见 `component-mapping.md`；标记契约见 `projection.manifest.yaml`。交付前必须跑 `scripts/audit_projection.py`。

---

## 一、硬性原则

1. **合法存储格式**：用 Confluence Storage Format XHTML（`<ac:structured-macro>` / `<ri:` 资源 / `<table>`），不是浏览器 HTML。
2. **严格投影**：每个意图块对回 `doc.md` 声明；不发明块、不改数字。
3. **数据同源**：`{{d:id}}` → datasets 值；不在成品里发明另一套数字。
4. **投影标记**：每个意图块前发 `<!-- doc:proj id=.. kind=.. -->`（HTML 注释在存储格式中合法、不显示，对账锚点）。

---

## 二、doc.md 元素 → Confluence 存储格式

| doc.md 元素 | Confluence 存储格式 | 备注 |
|-------------|---------------------|------|
| `# 标题` | `<h1>…</h1>`（或页面 title 用 `<h1>`） | 标题层级照搬 |
| `## 章节` | `<h2>…</h2>` | — |
| `{{d:id}}` | 纯文本 `value unit` | datasets 插值 |
| `[ref:id]` | `<a href="url">label</a>` | — |
| `> [!note]` | `<ac:structured-macro ac:name="info">` | 蓝色信息面板 |
| `> [!tip]` | `<ac:structured-macro ac:name="tip">` | 绿色提示 |
| `> [!warning]` | `<ac:structured-macro ac:name="warning">` | 红色警示 |
| `> [!important]` | `<ac:structured-macro ac:name="note">` | 黄色注意 |
| `> [!decision]` | `<ac:structured-macro ac:name="info">` 内含 **决策** 前缀 | 见 component-mapping §decision |
| `[badge:L text]` | `<ac:structured-macro ac:name="status">` + `ac:parameter name="title"/"colour"` | 见 component-mapping §status |
| ` ```chart ``` ` | `<ac:structured-macro ac:name="chart">`（含内嵌数据表）或 mermaid 宏 | 见 component-mapping §chart |
| ` ```mermaid ``` ` | `<ac:structured-macro ac:name="mermaid">` | 见 component-mapping §diagram |
| ` ```kpi ``` ` | 信息面板 `<ac:structured-macro ac:name="info">` + 大字段落 | — |
| ` ```timeline ``` ` | 原生 `<table>` | — |
| 原生表格 | Confluence `<table>` 存储格式 | 含 `<th>`/`<td>` |
| 代码块 | `<ac:structured-macro ac:name="code">` + `ac:parameter name="language"` | — |
| 列表 | `<ul>`/`<ol>` | — |

---

## 三、生成流程（机械投影）

1. 读 `doc.md`，解析 front-matter 得 datasets/figures/references。
2. 页面标题用 `<h1>`（或交付时提示用户填页面 title）。
3. 逐节扫描：
   - `{{d:id}}` → datasets 插值。
   - `[ref:id]` → `<a href>`。
   - fenced chart/kpi/timeline/mermaid → 按 component-mapping 转 macro，前置 `<!-- doc:proj ... -->`。
   - admonition → 对应宏（note/tip/warning/info），前置 `<!-- doc:proj id=.. kind=callout -->`。
   - `[badge:L text]` → status 宏。
   - 表格 → Confluence `<table>`，前置 `<!-- doc:proj id=.. kind=table -->`。
4. 写出 `<主题>.confluence.xhtml`（纯存储格式正文，不含 `<html>` 外壳）。

> 颜色/宏名严格按 component-mapping；决策/状态的颜色全文一致。

---

## 四、投影标记（对账锚点）

```
<!-- doc:proj id=impact_by_minute kind=chart:bar -->
<!-- doc:proj id=warning-1 kind=callout -->
<!-- doc:proj id=status-1 kind=status -->
```

> HTML 注释在 Confluence 存储格式中合法且不显示；交付后用户也可保留（不影响渲染）。**不得删除。**

---

## 五、交付前对账

```bash
python skills/doc-render/scripts/audit_projection.py <doc.md> <render-dir> --backend confluence
```

重点：`doc.md` 声明的每个块（id+kind）在成品里有对应 `doc:proj` 标记；无未声明块；`{{d:}}`/`[ref:]` 无残留；callout variant→宏名映射正确、status 颜色一致。
