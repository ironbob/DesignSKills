# 后端注册表：doc-render 支持的后端

> 用途：登记本 skill 支持的渲染后端、各后端的投影策略，以及**如何新增一个后端**（manifest 数据驱动，零 Python 改动）。
> 与 `scripts/audit_projection.py` 的抽取器策略一一对应。

---

## 一、已支持后端

| 后端 | 目录 | parse 策略 | 产物形态 | 投影标记 |
|------|------|-----------|----------|----------|
| Markdown | `references/markdown/` | `text_regex` | 干净可读 `.md`（图表→mermaid、状态→emoji、标注→admonition） | `<!-- doc:proj id=.. kind=.. -->` HTML 注释 |
| Confluence | `references/confluence/` | `text_regex` | 存储格式 XHTML（意图块→原生宏） | `<!-- doc:proj id=.. kind=.. -->` HTML 注释 |

每后端三件套（缺一不可）：

1. `render-template.md` —— 如何按 `doc.md` 写成品 + 投影标记契约。
2. `component-mapping.md` —— block kind → 该后端原生组件映射。
3. `projection.manifest.yaml` —— 标记怎么读（对账脚本的输入）。

> **后端注册表 = 文件系统**：`audit_projection.py` 自动扫描 `references/*/projection.manifest.yaml` 来发现后端，不维护硬编码后端列表。标记识别用的正则、未解析占位规则也都从该 manifest 编译而来——新增一个文本后端只需"加目录 + 三件套"，零 Python 改动（验证见下文 §四）。

---

## 二、parse 策略

`audit_projection.py` 的通用抽取器认 `text_regex` 策略（文档成品多为文本，HTML 注释标记跨后端通用）：

| `parse` | 适用 | 读法 |
|---------|------|------|
| `text_regex` | 文本型成品（Markdown、Confluence 存储 XHTML、Plain、Wiki…） | 命名捕获组正则（按行扫描） |

> 后续若新增 HTML 类后端需要 DOM 解析，可给抽取器加 `dom_html` 策略（仅此一处改动）。

---

## 三、投影标记契约（两后端统一）

每个投影块前发一条 HTML 注释标记（Markdown 与 Confluence 存储格式均合法、不显示）：

```
<!-- doc:proj id=<figure_id|block_id> kind=<block_kind> -->
```

- `id`：`figures[]` 的 id（图表/KPI）或正文块的顺序 id。
- `kind`：`doc-schema.md` 的 block kind（chart:bar / kpi / timeline / callout / status / table / diagram …）。
- 纯 `prose`/`list` 不强制标记（量大）；图表/KPI/timeline/callout/status/table-with-intent/diagram 必须标记。

`audit_projection.py` 抽取所有 `doc:proj` 标记，与 `doc.md` 声明的块（figures + 正文 fenced 块）逐一比对。

---

## 四、新增一个后端（零 Python 改动）

新增后端（如 Notion / Word）的步骤——**核心（解析/对账比较）不动，抽取器代码不动**：

1. **新建目录** `references/<后端>/`。
2. **写 `render-template.md`**：该后端如何按 `doc.md` 写成品；投影标记写法（复用 `<!-- doc:proj ... -->`）。
3. **写 `component-mapping.md`**：每个 block kind → 该后端原生组件。
4. **写 `projection.manifest.yaml`**：声明标记怎么读（多半复用 `text_regex`，只填 pattern）：
   ```yaml
   parse: text_regex
   block: { pattern: '<!--\s*doc:proj\s+id=(?P<id>\S+)\s+kind=(?P<kind>\S+)\s*-->' }
   ```
5. **在本表（§一）登记一行**。
6. **在 `SKILL.md` 的产出描述里加一项**。

完成 1–6，新后端即可被 `audit_projection.py --backend <后端>` 对账。

> 唯一需要改 Python 的情形：新后端标记形态 `text_regex` 套不上（如需 DOM 解析）。属罕见；此时给抽取器加一个 `parse` 策略。
