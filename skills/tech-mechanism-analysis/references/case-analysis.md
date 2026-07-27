# 边界与行为用例分析

## 目录

1. [目标与追溯链](#目标与追溯链)
2. [边界清单](#边界清单)
3. [可验证行为用例](#可验证行为用例)
4. [源码锚点](#源码锚点)
5. [验收用例](#验收用例)
6. [多入口与分支矛盾](#多入口与分支矛盾)
7. [Lite 输出](#lite-输出)
8. [Full JSON 契约](#full-json-契约)
9. [质量检查](#质量检查)

## 目标与追溯链

把机制说明转换为可复核、可验收的行为契约：

```text
边界 BOUNDARY-NN
  → 行为用例 CASE-NN
    → 源码锚点 file:line
    → 验收用例 ACCEPT-NN
```

另行比较同一机制的不同入口或分支：

```text
CASE-NN + CASE-MM
  → CONFLICT-NN（仅在行为契约互相矛盾时记录）
```

不要把“存在两个不同分支”直接写成矛盾。只有相同语义条件在不同入口或
分支产生互不兼容的默认值、状态变化、输出、副作用、异常、顺序或重试语义时，
才记录 `CONFLICT-NN`。

## 边界清单

至少主动复核以下类别，并把适用项、未确认项和对结论重要的不适用项写入清单：

- 空输入、缺字段、空集合；
- 下界、上界、精确端点、越界；
- 非法输入、非法状态、重复操作；
- 结束哨兵、取消、异常、超时；
- 并发、乱序、重入、背压；
- 动态解析失败、依赖失败；
- 资源上限和机制特有边界。

边界状态：

- `applicability=applicable`：该边界属于机制真实契约；
- `applicability=uncertain`：代码线索表明可能适用，但覆盖或运行证据不足；
- `applicability=not-applicable`：已检查且能说明为什么不适用；
- `verified`：已运行原实现、已有测试或等价求值，观察结果与记录一致；
- `partially-verified`：只验证了部分入口、分支或环境；
- `unverified`：只完成静态定位，未观察运行结果；
- `not-applicable`：已检查且能说明为什么不适用。

取消、异常、并发和背压是强制覆盖类别。无论是否存在对应实现分支，最终清单都
必须各有一项，并明确 `applicability` 与验证状态。不得因“没有看到处理代码”而
省略；这通常应记录为 `uncertain + unverified` 或有依据的
`not-applicable + not-applicable`。

`verified`、`partially-verified` 和 `unverified` 必须挂至少一个源码锚点。
`verified` 和 `partially-verified` 必须关联至少一个 `CASE-NN`。
`not-applicable` 可不挂源码锚点，但必须在 `observed_behavior` 说明判定依据。

## 可验证行为用例

行为用例描述一个可以独立复核的入口和分支，不等同于实现阶段摘要。每条包含：

- 稳定编号和标题；
- 入口 `entry_point`；
- 分支 `branch_path`；
- 语义条件键 `semantic_key`；
- 前置条件；
- 输入；
- 动作；
- 期望可观察行为；
- 实际观察行为；
- 验证方式、步骤、状态和结果；
- 源码锚点；
- 对应验收用例编号。

验证状态与方法：

| `status` | 允许的 `method` | 含义 |
|---|---|---|
| `verified` | `test` / `command` / `equivalent-evaluation` | 已得到运行结果 |
| `static-only` | `inspection` | 只完成静态取证 |
| `not-run` | `not-run` | 当前环境没有执行 |

`procedure` 必须足够具体，使另一位分析者能复现。例如写测试名、最小调用步骤或
命令；不要只写“已验证”。`observed_result` 必须记录实际看到的值、状态、异常或
副作用。`static-only` / `not-run` 不得伪造运行结果。

`semantic_key` 使用 kebab-case，标识与入口无关的同一业务/协议条件，例如
`missing-plugin-method`。左右越界必须分别使用
`time-before-first-frame` 和 `time-after-last-frame`，因为它们是两个合法且不同的
边界语义，不能仅因返回不同端点值而形成矛盾。

## 源码锚点

`source_anchors` 使用统一结构：

```json
{
  "file": "src/cache.ts",
  "line": 42,
  "note": "空 key 分支直接返回 miss"
}
```

要求：

- 使用 repo-root 相对路径和有效正整数行号；
- 文件必须属于 `covered_files`；
- `note` 说明该行支持的具体行为，不只写函数名；
- 优先锚定分支条件、状态写入、返回、抛错或最终副作用；
- 一条锚点不能代替跨文件或跨分支的全部证据；
- 现有测试可以作为补充锚点，但不能代替真实实现锚点。

## 验收用例

验收用例把分析结论转换为 Given / When / Then：

- `given`：初始状态、依赖和数据；
- `when`：从哪个入口执行什么动作；
- `then`：可观察且可判定通过/失败的结果；
- `verification_level`：`automated` 或 `manual`；
- `behavior_case_ids`：它验收的行为用例；
- `source_anchors`：该预期对应的实现位置。

每个 `CASE-NN` 至少关联一个 `ACCEPT-NN`，且两侧引用必须一致：

```text
CASE-01.acceptance_case_ids 包含 ACCEPT-01
ACCEPT-01.behavior_case_ids 包含 CASE-01
```

验收用例描述“应当满足什么”，行为用例记录“当前实现实际表现什么”。二者不一致
时不能偷偷改写实际行为：保留差异，并在 `gaps` 或 `behavior_conflicts` 说明。

## 多入口与分支矛盾

先按相同语义条件对齐用例，再比较：

1. 输入标准化与默认值；
2. 返回值、错误类型和错误传播；
3. 状态变化、持久化和副作用；
4. 取消、重试、超时和终止；
5. 同步/异步顺序与并发保证；
6. 动态分派和直接调用的契约。

`behavior_conflicts[]` 每项必须：

- 引用至少两个不同 `CASE-NN`；
- 所引用用例的 `semantic_key` 必须完全相同；
- 被引用用例的 `(entry_point, branch_path)` 至少有一项不同；
- 写明比较维度、不可兼容之处和影响；
- 用 `intent_status` 区分 `intentional` / `unintentional` / `unknown`；
- 给出收敛或确认方向，不把建议写成已实施事实；
- 挂支持各侧行为的源码锚点。

若没有发现矛盾，仍输出“未识别到多入口/分支行为矛盾”。若入口未枚举完整，把
“未识别到”限定在已覆盖入口，并在 `gaps` 记录缺口。

## Lite 输出

Lite Markdown 在 `全链路` 后、`数值示例` 前固定增加：

1. `## 边界清单`：`### BOUNDARY-NN · 标题`；
2. `## 可验证行为用例`：`### CASE-NN · 标题`；
3. `## 验收用例`：`### ACCEPT-NN · 标题`；
4. `## 多入口/分支行为矛盾`：有则使用 `### CONFLICT-NN · 标题`，无则明确写无。

frontmatter 同步记录：

```yaml
boundaries: 4
behavior_cases: 3
acceptance_cases: 3
behavior_conflicts: 0
```

Lite 至少输出一个边界、一个行为用例和一个验收用例。每个块的字段与 Full
同名语义保持一致；行为用例和验收用例都必须包含有效 `file:line` 源码锚点。

## Full JSON 契约

### `boundary_inventory[]`

```json
{
  "id": "BOUNDARY-01",
  "kind": "empty-input",
  "applicability": "applicable",
  "condition": "轨道没有关键帧",
  "expected_contract": "采样返回零值且不进入插值",
  "observed_behavior": "sampleAt 直接返回 0",
  "status": "verified",
  "behavior_case_ids": ["CASE-01"],
  "source_anchors": [
    {"file": "src/keyframe.ts", "line": 26, "note": "空轨道守卫返回 0"}
  ]
}
```

`applicability` 为 `applicable` / `uncertain` / `not-applicable`。

`kind` 为 `empty-input` / `lower-bound` / `upper-bound` / `invalid-input` /
`invalid-state` / `terminal-sentinel` / `cancellation` / `exception` / `timeout` /
`concurrency` / `backpressure` / `dynamic-resolution` / `resource-limit` / `custom`。
每份分析必须包含 `cancellation`、`exception`、`concurrency` 和 `backpressure`。

### `behavior_cases[]`

```json
{
  "id": "CASE-01",
  "title": "空轨道采样",
  "boundary_ids": ["BOUNDARY-01"],
  "entry_point": "KeyframeTrack.sampleAt",
  "branch_path": "frames.length === 0",
  "semantic_key": "empty-keyframe-track",
  "preconditions": ["frames=[]"],
  "input": "t=5",
  "action": "调用 sampleAt(5)",
  "expected_observable": "返回 0",
  "observed_observable": "原实现返回 0",
  "verification": {
    "status": "verified",
    "method": "command",
    "procedure": "运行 Node 最小调用并读取 JSON 输出",
    "observed_result": "empty=0"
  },
  "source_anchors": [
    {"file": "src/keyframe.ts", "line": 26, "note": "空轨道返回 0"}
  ],
  "acceptance_case_ids": ["ACCEPT-01"]
}
```

### `acceptance_cases[]`

```json
{
  "id": "ACCEPT-01",
  "title": "空轨道使用零值兜底",
  "behavior_case_ids": ["CASE-01"],
  "given": "一个没有关键帧的轨道",
  "when": "在任意时间调用 sampleAt",
  "then": "返回 0，且不读取端点或执行插值",
  "verification_level": "automated",
  "source_anchors": [
    {"file": "src/keyframe.ts", "line": 26, "note": "守卫在端点读取前返回"}
  ]
}
```

### `behavior_conflicts[]`

```json
{
  "id": "CONFLICT-01",
  "title": "两个入口对缺失标识采用不同错误契约",
  "case_ids": ["CASE-03", "CASE-04"],
  "comparison_dimension": "error-contract",
  "contradiction": "HTTP 入口返回 not-found，内部入口抛出 KeyError",
  "impact": "调用方无法复用统一重试和错误映射策略",
  "intent_status": "unknown",
  "resolution": "确认统一错误契约，或明确记录入口适配差异",
  "source_anchors": [
    {"file": "src/http.py", "line": 40, "note": "HTTP 入口映射为 not-found"},
    {"file": "src/core.py", "line": 18, "note": "内部入口直接抛出 KeyError"}
  ]
}
```

`comparison_dimension` 使用非空短语，不限制领域词表。`behavior_conflicts` 可为空，
但报告章节不可省略。

## 质量检查

- 边界清单不是只抄 `if`；要写条件、契约、实际行为和验证状态。
- 行为用例不是阶段摘要；必须能独立触发并观察结果。
- `verified` 必须来自运行证据，不得只因看到源码分支就标记。
- 每个行为用例至少一个源码锚点和一个验收用例。
- 验收 Then 必须可判定，避免“正常工作”“符合预期”。
- 矛盾记录必须比较相同语义条件，不把合法的输入差异当矛盾。
- 左右越界、成功/失败、存在/缺失等不同语义条件不得共用 `semantic_key`。
- 找不到多入口或分支时如实写覆盖限制，不制造 `CONFLICT-NN`。
