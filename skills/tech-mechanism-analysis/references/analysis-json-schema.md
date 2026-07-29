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
| `boundary_coverage` | object | 取消/异常/并发/背压四个键必须齐全；背压回指 `flow-control`，其余回指同名边界 |
| `boundary_inventory` | object[] | 非空，边界检查与验证状态 |
| `behavior_cases` | object[] | 非空，可独立复核的入口/分支行为 |
| `acceptance_cases` | object[] | 非空，与行为用例双向关联 |
| `behavior_conflicts` | object[] | 可空，多入口/分支行为矛盾 |
| `numerical_examples` | object[] | 可空 |
| `defects` | object[] | 可空 |
| `diagrams` | object | 必填；业务流程图、时序图、架构角色图全部存在 |
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

## 边界与行为用例

`boundary_inventory[]`、`behavior_cases[]`、`acceptance_cases[]` 和
`behavior_conflicts[]` 的完整字段、枚举、追溯规则与示例见
`references/case-analysis.md`。核心约束：

- 每个边界、行为用例、验收用例和矛盾记录使用稳定且唯一的编号；
- 每个行为用例必须挂源码锚点并至少对应一个验收用例；
- 行为用例与验收用例的引用必须双向一致；
- 取消、异常、并发、背压必须在独立 `boundary_coverage` 中各自回指真实条目；
- 每个边界分开记录适用性、处理能力和验证状态；无界队列的背压处理能力为 `unsupported`；
- `verified` 行为用例必须使用运行型验证方法；
- 矛盾必须引用具有相同 `semantic_key`、但来自不同入口或分支的行为用例；
- `behavior_conflicts` 为空时，最终 Markdown 仍必须输出“未识别到”结论。

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

## `evidence[]` 与 `source_anchors[]`

两者使用相同基础结构，每项必须有：

- `file`：规范化的 repo-root 相对路径，不得使用绝对路径或 `..`；Full 中必须属于 `covered_files`
- `line`：正整数
- `note`：该位置支持的具体事实

## `diagrams`

三图全部必填，不允许 `applicable=false`：

```json
{
  "business_flow": {
    "type": "flowchart",
    "nodes": [
      {
        "id": "request",
        "label": "调用方请求采样",
        "evidence": [{"file": "src/renderer.ts", "line": 9, "note": "每帧请求采样"}]
      }
    ],
    "edges": [
      {
        "from": "request",
        "to": "effect",
        "label": "采样并写入",
        "evidence": [{"file": "src/renderer.ts", "line": 10, "note": "写入目标属性"}]
      }
    ]
  },
  "sequence": {
    "type": "sequence",
    "nodes": [
      {
        "id": "binding",
        "label": "PropertyBinding",
        "evidence": [{"file": "src/renderer.ts", "line": 4, "note": "绑定类"}]
      }
    ],
    "edges": [
      {
        "from": "binding",
        "to": "track",
        "label": "sampleAt(time)",
        "evidence": [{"file": "src/renderer.ts", "line": 9, "note": "请求采样"}]
      }
    ]
  },
  "architecture_roles": {
    "type": "architecture",
    "nodes": [
      {
        "id": "track",
        "label": "KeyframeTrack",
        "entity_type": "class",
        "role": "保存有序关键帧并按时间采样",
        "evidence": [{"file": "src/keyframe.ts", "line": 14, "note": "轨道类"}]
      }
    ],
    "edges": [
      {
        "from": "binding",
        "to": "track",
        "label": "调用采样",
        "evidence": [{"file": "src/renderer.ts", "line": 9, "note": "依赖采样接口"}]
      }
    ]
  }
}
```

约束：

- `business_flow.type=flowchart`，至少 2 个节点和 1 条边；
- `sequence.type=sequence`，至少 2 个参与者和 1 条消息；
- `architecture_roles.type=architecture`，至少 2 个角色和 1 条关系；
- `artifact` 可选；存在时必须且只能包含 `tool` 和 `file`，工具为
  `graphviz` / `plantuml` / `structurizr` / `other`，文件为 repo-root
  相对 `.svg` / `.png` 路径；渲染器将嵌入该文件而不是 Mermaid；
- 节点 ID 匹配 `[A-Za-z_][A-Za-z0-9_]*` 且在单图内唯一；
- 标签、角色和边标签为单行文本；
- 架构节点额外必填 `entity_type` 和具体动作职责 `role`；
- `entity_type` 为 `class` / `module` / `service` / `function` /
  `data-store` / `external`；
- 每个节点和边都必须有属于 `covered_files` 的证据。

外部图回退示例（加到任一图对象中）：

```json
"artifact": {
  "tool": "graphviz",
  "file": "docs/diagrams/business-flow.svg"
}
```

JSON 中禁止 `mermaid`；Markdown 的三张图和结构清单由渲染器生成。

## 禁止键

任何层级禁止：`severity`、`bug`、`repro`、`mermaid`。

基础数据流完整示例见 `examples/2026-07-23-example-analysis.json`；异步、状态机和反射/动态分派示例见 `references/validation-matrix.md`。
