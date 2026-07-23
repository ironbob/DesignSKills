# analysis.json Schema —— 技术机制深度分析契约源

> 配合 `tech-mechanism-analysis` 的 Checklist 第 8 步使用。`analysis.json` 是**唯一事实源**：它把「机制类型 + 链路分段 + 数值工作举例 + 双轴设计债」结构化成机器可判的契约，`analysis.md` 是它的渲染，`validate_analysis.py` / `validate_evidence.py` / `validate_contract.py` 对它做强校验。两者必须一致。

## 设计原则

1. **契约即源** —— `analysis.json` 先于 `analysis.md` 定稿；md 的 id、段覆盖、计数都从它派生并对账。
2. **每条可定位** —— 每个链路段、数值举例、缺陷都挂 `evidence`（file:line / 类 / 函数 / 调用点）；定位不到的标 `⚠ 未确认` 并登记 `gaps`，**禁止编造证据**。`validate_evidence.py` 轻量校验证据文件、行号、note 关键字。
3. **数值举例忠实于代码** —— 每个 `numerical=true` 的链路段必须有 ≥1 条 `numerical_examples`；每条带逐步运算 + `faithfulness_note`（声明与原代码一致 / 是否做了代码翻译）。
4. **缺陷 = 设计债，不是 bug** —— 每条 defect 四要素（`hard_requirement` / `why_hard` / `evolution_direction` / `cost_impact`）全必填非空；**严禁出现 `severity` / `bug` 字段**（脚本硬卡 ERROR）。
5. **机制类型是假设** —— `mechanism_type` + `mechanism_type_basis` 必填；套用的 `chain_template` 与 `chain_stages[].segment` 一一对应。
6. **Mermaid 是 md 派生产物** —— JSON 中**禁止 `mermaid` 字段**（脚本硬卡）；链路图在 md 内嵌，首版不做 render 脚本对账。

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target` | string | ✅ | 机制名（kebab-case），与 report frontmatter 一致 |
| `analyzed_at` | string | ✅ | 分析日期 `YYYY-MM-DD` |
| `languages` | string[] | ✅ | 识别到的主要语言，**非空**（多语言全列） |
| `language_precision` | object[] | ✅ | 各语言精度，每项 `{language, precision, note}`；`precision` ∈ `high`/`medium`/`low`；与 `languages` 一一对应 |
| `covered_files` | string[] | ✅ | 本次覆盖文件/目录集合，**非空** |
| `responsibility` | string | ✅ | 一句话机制职责（它做什么，非「应有设计」） |
| `mechanism_type` | string | ✅ | `data-flow` / `lifecycle` / `call-chain` / `state-machine` / `other` |
| `mechanism_type_basis` | string | ✅ | 判为该类型的依据（对照具体机制） |
| `chain_template` | string[] | ✅ | 套用的链路分段名，**非空**（如 `["produce","flow","process","effect"]`） |
| `chain_stages` | object[] | ✅ | 链路分段，**非空**，每段 `segment` 须在 `chain_template` 内 |
| `numerical_examples` | object[] | ✅ | 数值工作举例；每个 `numerical=true` 段须 ≥1 条；可空仅当全链路无数值段 |
| `defects` | object[] | ✅ | 设计债清单；允许为空 `[]` |
| `diagrams` | object | 否 | P2 链路可视化（结构化，不含 mermaid）；可省略 |
| `gaps` | string[] | ✅ | 已知缺口；可空 `[]` |

> **全文禁止键**：任何层级出现 `severity`、`bug`、`mermaid` 键均 ERROR（分别守住「不打分级」「缺陷≠bug」「mermaid 不进 json」）。

## chain_stages 字段（逐段）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 稳定 id（如 `stage-produce`）；全文件唯一；`^[A-Za-z][A-Za-z0-9_-]*$` |
| `segment` | string | ✅ | 对应 `chain_template` 中某项 |
| `name` | string | ✅ | 段名（人读，如「产生：关键帧存储」） |
| `what` | string | ✅ | 这段做了什么 |
| `how` | string | ✅ | 怎么实现（数据结构 / 算法 / 调用点） |
| `why` | string | ✅ | 为什么这么设计 |
| `key_structures` | string[] | ✅ | 关键数据结构 / 类 / 函数，**非空** |
| `numerical` | bool | ✅ | 该段是否含数值计算（true 则必须有 numerical_example） |
| `handoff` | string | 否 | 与下一段的衔接约定（数据格式 / 接口 / 时序 / 隐含假设） |
| `evidence` | object[] | ✅ | 证据，**非空**，每项 `{file, line?, note}` |

## numerical_examples 字段（★ 签名能力）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | `NUM-NN`；全文件唯一 |
| `stage_id` | string | ✅ | 引用一个 `chain_stages[].id`，且该段 `numerical=true` |
| `operation` | string | ✅ | 运算名（如「ease-in-out 插值」「EMA 平滑」） |
| `sample_data` | string | ✅ | 具体示例数据（适度规模，非平凡） |
| `computation_steps` | string[] | ✅ | 逐步实际运算，**非空**，每步可核 |
| `result` | string | ✅ | 运算结果 |
| `code_translation` | string | 否 | 若对代码做了等价翻译（如转 Python 求值），记录翻译方式与译文要点 |
| `faithfulness_note` | string | ✅ | **声明运算逻辑与原代码一致**（含是否做了翻译、保留了哪些影响结果的步骤） |
| `evidence` | object[] | ✅ | 证据（指向被举例的代码），**非空** |

## defects 字段（★ 设计债）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | `DEBT-ARCH-NN`（架构轴）或 `DEBT-LOGIC-NN`（逻辑轴）；全文件唯一 |
| `axis` | string | ✅ | `architecture` / `logic`；须与 id 前缀一致 |
| `stage_id` | string | ✅ | 引用一个 `chain_stages[].id` |
| `cross_stage` | bool | ✅ | 是否跨段衔接缺陷（true 单列为衔接专项） |
| `title` | string | 否 | 一句话标题 |
| `hard_requirement` | string | ✅ | ★ 会变难的具体需求（具体可描述，非空话） |
| `why_hard` | string | ✅ | ★ 当前设计哪里让它难 |
| `evolution_direction` | string | ✅ | ★ 演进 / 松绑方向（真要做这需求，设计怎么改） |
| `cost_impact` | string | ✅ | ★ 代价 / 影响评估（改动面 / 涉及哪些段 / 风险） |
| `evidence` | object[] | ✅ | 证据，**非空** |

> **严禁字段**：`severity`、`bug`、`repro`（出现即 ERROR，守住「设计债 ≠ bug、不打分级」）。演进只指方向，不到完整重构方案。

## diagrams 字段（P2，可选）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `applicable` | bool | ✅ | 是否适用链路可视化 |
| `reason` | string | false 时必填 | 不适用原因 |
| `type` | string | true 时必填 | `sequence` / `flowchart` / `state` |
| `nodes` | object[] | true 时必填 | 每项 `{id, label, evidence[]}`；id 唯一 |
| `edges` | object[] | true 时必填 | 每项 `{from, to, label?, evidence[]}`；端点须引用已声明 node |

> 出现 `mermaid` 键即 ERROR。md 中对应章节内嵌 Mermaid，首版不做逐块对账（无 render 脚本）。

## 通用 evidence 子结构

`evidence[]` 每项：`{file, line?, note}` —— `file` 相对 repo root 或绝对路径；`line` 可缺省（表示类/模块级证据）；`note` 说明该证据指向什么（`validate_evidence.py` 会校验 note 含机制相关关键字，防无意义占位）。

## 校验要点（对应脚本）

- `validate_analysis.py`：顶层字段与类型；`mechanism_type` 枚举；`chain_stages` 非空且每段 `segment` ∈ `chain_template`、`evidence` 非空；**每个 `numerical=true` 段有 ≥1 条 numerical_example 且 stage_id 匹配**；**每个 defect 四要素非空、axis 与 id 前缀一致、stage_id 引用真实段**；**全文拒绝 `severity`/`bug`/`mermaid` 键**；id 唯一。
- `validate_evidence.py`：递归遍历所有 `evidence[]`，校验文件存在、行号范围、note 关键字命中。
- `validate_report.py`：analysis.md 的 frontmatter / 章节关键词 / 每条 defect 四要素 / banned 词 / 未确认标注。
- `validate_contract.py`：json↔md 对账（每个 `DEBT-*`/`NUM-*` id 在 md 出现、计数 / `covered_files` / `mechanism_type` / 链路段数对齐、无悬空）。

## 完整示例

以 `examples/2026-07-23-example-analysis.json` 为准（关键帧缓动机制）。确认结构合法后运行：

```bash
python3 scripts/validate_analysis.py examples/2026-07-23-example-analysis.json
```
