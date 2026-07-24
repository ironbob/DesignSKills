# Full `analysis.json` 契约

Lite 不使用 JSON。本契约仅用于 `mode: full`。

## 顶层字段

| 字段 | 类型 | 约束 |
|---|---|---|
| `mode` | string | 必须为 `full` |
| `target` | string | kebab-case |
| `analyzed_at` | string | `YYYY-MM-DD` |
| `languages` | string[] | 非空、唯一 |
| `language_analysis` | object[] | 与 languages 一一对应 |
| `covered_files` | string[] | 非空、唯一，只列真实文件 |
| `responsibility` | string | 一句话职责 |
| `mechanism_type` | string | `data-flow` / `lifecycle` / `call-chain` / `state-machine` / `other` |
| `secondary_mechanism_types` | string[] | 可空，不含主类型 |
| `mechanism_type_basis` | string | 类型判据 |
| `chain_template` | string[] | 与阶段 segment 按顺序一一对应 |
| `chain_stages` | object[] | 非空 |
| `numerical_examples` | object[] | 可空 |
| `defects` | object[] | 可空 |
| `diagrams` | object | 可选 |
| `gaps` | string[] | 可空、唯一 |

`language_analysis[]`：

```json
{
  "language": "TypeScript",
  "confidence": "high",
  "basis": "入口、全部调用点和运行结果均已验证",
  "tools": ["text search", "type checker", "test"]
}
```

`confidence` 为 `high` / `medium` / `low`。

## `chain_stages[]`

必填字段：

- `id`：稳定且唯一。
- `segment`：与 `chain_template` 同位置相等。
- `name`、`what`、`how`、`why`。
- `why_basis`：`observed` / `inferred` / `unknown`。
- `key_structures`：非空字符串数组。
- `numerical`：布尔值。
- `handoff`：非空；最后一段描述最终效果。
- `evidence`：非空。

当 `why_basis=unknown` 时，`why` 应直接说明代码无法证明设计意图；不得伪造动机。

## `numerical_examples[]`

- `id`：`NUM-NN`
- `stage_id`：引用 `numerical=true` 的阶段
- `operation`
- `sample_data`
- `computation_steps`：至少两步
- `result`
- `code_translation`：可选
- `faithfulness_note`
- `evidence`

每个数值阶段至少一个示例。

## `defects[]`

- `id`：`DEBT-ARCH-NN` 或 `DEBT-LOGIC-NN`
- `axis`：`architecture` / `logic`，与 ID 一致
- `stage_id`
- `cross_stage`
- `title`
- `requirement_source`：`user` / `roadmap` / `issue` / `code-evolution` / `hypothetical`
- `hard_requirement`
- `why_hard`
- `evolution_direction`
- `cost_impact`
- `confidence`：`high` / `medium` / `low`
- `confidence_basis`
- `evidence`

置信度是证据强弱，不是严重度。

## `evidence[]`

每项必须有：

- `file`：相对 repo root 或绝对路径；Full 中必须属于 `covered_files`
- `line`：正整数
- `note`：该位置支持的具体事实

## `diagrams`

可选：

```json
{
  "applicable": true,
  "type": "flowchart",
  "nodes": [{"id": "produce", "label": "写入", "evidence": []}],
  "edges": [{"from": "produce", "to": "effect", "label": "value", "evidence": []}]
}
```

节点 ID 唯一，边端点必须存在。JSON 中禁止 `mermaid`；Markdown 图由渲染器生成。

## 禁止键

任何层级禁止：`severity`、`bug`、`repro`、`mermaid`。

完整示例见 `examples/2026-07-23-example-analysis.json`。
