# Full `analysis.json` 契约

Lite 不使用 JSON。本契约仅用于 `mode: full`。

## 顶层字段

| 字段 | 类型 | 约束 |
|---|---|---|
| `mode` | string | 必须为 `full` |
| `target` | string | kebab-case |
| `analyzed_at` | string | `YYYY-MM-DD` |
| `scope_confirmations` | object[] | 非空，按确认顺序记录，最后一项与当前范围一致 |
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

除文档列出的字段外禁止额外键，避免拼写错误被静默接受。
所有日期严格使用扩展日历格式 `YYYY-MM-DD`；稳定编号中的 `NN` 表示至少两位数字。

`scope_confirmations[]`：

```json
{
  "id": "SCOPE-01",
  "confirmed_at": "2026-07-23",
  "trigger": "initial",
  "target": "keyframe-easing",
  "mechanism_type": "data-flow",
  "responsibility": "用户确认的候选职责",
  "candidate_files": ["src/keyframe.ts"],
  "confirmation_basis": "用户在当前任务中明确回复确认该候选范围"
}
```

`trigger` 为 `initial` / `material-expansion`。最后一项的 target、类型和职责必须与顶层当前值一致。候选文件使用 repo-root 相对路径并指向真实文件；候选文件允许在追踪后被判定为与机制无关，因此不强制全部进入最终 `covered_files`。

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

- `id`：稳定且唯一，匹配 `stage-[a-z0-9]+(?:-[a-z0-9]+)*`。
- `segment`：与 `chain_template` 同位置相等。
- `name`、`what`、`how`、`why`。
- `why_basis`：`observed` / `inferred` / `unknown`。
- `why_evidence`：数组。`observed` 时必须非空，且每项额外包含
  `source_type: adr / documentation / issue / explicit-comment`；其他依据时必须为空。
- `key_structures`：非空字符串数组。
- `numerical`：布尔值。
- `handoff`：非空；最后一段描述最终效果。
- `handoff_evidence`：非空，独立支持交接约定或最后一段的最终效果。
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
- `cost_quantification`：
  - `affected_stages`：非空、唯一，引用真实阶段；
  - `affected_files`：非空、唯一，属于 `covered_files`；
  - `affected_modules`：可空、唯一；
  - `change_scale`：`small` / `medium` / `large`；
  - `basis`：基于已读代码的量化依据。
- `confidence`：`high` / `medium` / `low`
- `confidence_basis`
- `evidence`

置信度是证据强弱，不是严重度。

## `evidence[]`

每项必须有：

- `file`：规范化的 repo-root 相对路径，不得使用绝对路径或 `..`；Full 中必须属于 `covered_files`
- `line`：正整数
- `note`：该位置支持的具体事实

## `diagrams`

可选：

```json
{
  "applicable": true,
  "type": "flowchart",
  "nodes": [{"id": "produce", "label": "写入", "evidence": [{"file": "src/keyframe.ts", "line": 18, "note": "写入关键帧"}]}],
  "edges": [{"from": "produce", "to": "effect", "label": "value", "evidence": [{"file": "src/keyframe.ts", "line": 40, "note": "插值结果交给写入端"}]}]
}
```

节点 ID 必须匹配 `[A-Za-z_][A-Za-z0-9_]*` 且唯一，标签必须为单行文本，边端点必须存在，节点和边证据均非空。信息不足时使用：

```json
{"applicable": false, "reason": "缺少运行时参与者关系，无法形成可靠图"}
```

JSON 中禁止 `mermaid`；Markdown 图由渲染器生成。

## 禁止键

任何层级禁止：`severity`、`bug`、`repro`、`mermaid`。

完整示例见 `examples/2026-07-23-example-analysis.json`。
