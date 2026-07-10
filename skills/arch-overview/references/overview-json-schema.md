# overview.json Schema —— 机器可判的总览契约源

> 配合 `arch-overview` 的 Checklist 第 8 步使用。`overview.json` 是**唯一事实源**：它把「3 视角图的结构化定义 + 4 维评估 + 业界做法对照 + 亮点/风险」结构化成机器可判的契约，`overview.md` 是它的渲染，`validate_overview.py`/`validate_evidence.py`/`validate_contract.py` 对它做强校验。两者必须一致。

## 设计原则

1. **契约即源** —— `overview.json` 先于 `overview.md` 定稿；`overview.md` 的档位、id、覆盖集合都从它派生并对账。
2. **每条可定位** —— 图节点/边/流转步、维度评估、亮点/风险都挂 `evidence`（file:line / 包 / 模块 / 依赖边）；定位不到的标对应项 `unconfirmed`/`⚠ 未确认` 并登记 `gaps`，**禁止编造证据**。`validate_evidence.py` 轻量校验证据文件、行号、note 关键字。
3. **每维可解释** —— `grade`（优/良/中/差）带客观依据（现状 + 业界差距），非主观打分。
4. **业界对照 provenance 透明** —— 每维 `industry_practice` 必须声明 `provenance="LLM内置经验"` + `verified=false` + `further_reading`，不联网不假装权威。
5. **3 视角适用性显式** —— 每视角 `applicable` 必填；`true` 须有完整结构化字段，`false` 须有 `reason`。
6. **Mermaid 是派生产物** —— JSON 中禁止 `mermaid` 字段；运行 `render_mermaid.py` 从结构生成，`validate_contract.py` 校验报告中的生成块没有漂移。

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target` | string | ✅ | 模块/app 名（kebab-case），与 report frontmatter 一致 |
| `analyzed_at` | string | ✅ | 分析日期 `YYYY-MM-DD` |
| `scope_level` | string | ✅ | `module` 或 `app` |
| `languages` | string[] | ✅ | 识别到的主要语言，**非空**（多语言全列） |
| `language_precision` | object[] | ✅ | 各语言精度，每项 `{language, precision, note}`；`precision` ∈ `high`/`medium`/`low` |
| `covered_files` | string[] | ✅ | 本次覆盖文件/目录集合，**非空** |
| `responsibility` | string | ✅ | 一句话架构职责（它声称做什么，非「应有架构」） |
| `overall_grade` | string | ✅ | 整体档位 `优`/`良`/`中`/`差`（汇总见 `scoring-and-grading.md §二`） |
| `dimensions` | object[] | ✅ | 4 维评估，**恰好 4 条**，`key` 集合 = `{layering, cohesion, extensibility, readability}` |
| `highlights` | object[] | ✅ | 亮点清单；允许为空 `[]` |
| `risks` | object[] | ✅ | 风险点清单；允许为空 `[]` |
| `diagrams` | object | ✅ | 3 视角图，键固定 `{layering, c4, runtime}` |
| `gaps` | string[] | ✅ | 已知缺口；可空 `[]` |

## dimensions 字段（4 维，顺序固定）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `key` | string | ✅ | `layering`/`cohesion`/`extensibility`/`readability`；4 条须覆盖全部且不重复 |
| `grade` | string | ✅ | `优`/`良`/`中`/`差` |
| `assessment` | string | ✅ | 现状评价（具体可核，不空泛） |
| `industry_practice` | object | ✅ | 业界做法对照，见下（6 个子字段全必填） |
| `evidence` | object[] | ✅ | 证据清单，**非空**，每项 `{file, line?, note}` |

### industry_practice 子字段（全必填）

| 字段 | 类型 | 说明 |
|------|------|------|
| `what` | string | 该做法是什么 |
| `when` | string | 适用前提/场景 |
| `gap` | string | 现状与标杆的差距方向 |
| `provenance` | string | 固定 `"LLM内置经验"` |
| `verified` | bool | 固定 `false`（未核对原文） |
| `further_reading` | string[] | ≥1 个可检索延伸方向（经典资料名/模式名/关键词） |

## highlights / risks 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 稳定 id：亮点 `HL-NN`、风险 `RISK-NN`；**全文件唯一** |
| `title` | string | ✅ | 一句话标题 |
| `dimension` | string | ✅ | 指向维度 key（`layering`/`cohesion`/`extensibility`/`readability`） |
| `note` | string | risks 必填 | 风险点前瞻性描述（未来什么场景下可能怎样）；highlights 可省 |
| `evidence` | object[] | ✅ | 证据清单，**非空**，每项 `{file, line?, note}` |

> risks 的 `note` 是前瞻性描述，**不含分级、不含 go/no-go、不含重构方案**（越界检查）。

## diagrams 字段（3 视角）

每个视角对象共用 `applicable`（bool）。`true` 时须有对应结构；`false` 时须有 `reason`。任何视角出现 `mermaid` 字段均为错误。

### diagrams.layering（视角①分层/模块依赖）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `applicable` | bool | ✅ | 几乎都 true |
| `reason` | string | false 时必填 | 不适用原因 |
| `direction` | string | 否 | `TD`/`LR` 等，默认 `TD` |
| `groups` | object[] | true 时必填 | 每项 `{id,label}`，层/subgraph 定义，id 唯一 |
| `nodes` | object[] | true 时必填 | 每项 `{id,label,group,evidence[]}`，id 唯一、group 必须存在 |
| `edges` | object[] | true 时必填 | 每项 `{from,to,label?,style?,evidence[]}`；端点必须存在，style 为 normal/dashed/strong |

### diagrams.c4（视角②C4 Container/Component）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `applicable` | bool | ✅ | |
| `reason` | string | false 时必填 | |
| `level` | string | true 时必填 | `container` 或 `component` |
| `nodes` | object[] | true 时必填 | 每项 `{id, label, kind, evidence[]}`；`kind` ∈ `service`/`component`/`store`/`external`/`actor` |
| `edges` | object[] | true 时必填 | 每项 `{from,to,label?,style?,evidence[]}`；端点必须存在 |

### diagrams.runtime（视角③运行时/数据流）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `applicable` | bool | ✅ | 纯库模块可能 false |
| `reason` | string | false 时必填 | 如「纯库模块无运行时入口」 |
| `type` | string | true 时必填 | `sequence` 或 `flowchart` |
| `participants` | object[] | true 时必填 | 每项 `{id,label,evidence[]}`，id 唯一 |
| `flows` | object[] | true 时必填 | 每项 `{step,from,to,action,kind?,evidence[]}`；端点引用 participant；sequence kind 为 sync/response/async/dashed |

### 通用 evidence 子结构

`evidence[]` 每项：`{file, line?, note}` —— `file` 相对 repo root 或绝对路径；`line` 可缺省（表示包/模块级证据）；`note` 说明该证据指向什么。

## 校验要点（对应脚本）

- `validate_overview.py`：严格检查顶层类型、语言对应关系、4 维结构，以及图 group/node/participant id 唯一、边/流端点引用、每项证据非空，并拒绝 JSON 中的 `mermaid` 字段。
- `validate_evidence.py`：递归遍历所有 `evidence[]`（dimensions/highlights/risks/diagrams 各结构），校验文件存在、行号范围、note 关键字命中。
- `render_mermaid.py`：从结构化 diagrams 确定性生成 Mermaid。
- `validate_contract.py`：除字段与 id 对账外，按固定视角顺序比较每个 Mermaid 块与结构化生成结果，任一字符漂移均失败。

## 完整示例

以 `examples/2026-07-10-example-overview.json` 为准。确认结构合法后运行：

```bash
python3 scripts/render_mermaid.py examples/2026-07-10-example-overview.json --format markdown
```
