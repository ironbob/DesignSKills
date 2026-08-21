# findings.json v2 契约

`findings.json` 是唯一事实源；`report.md` 必须由 renderer 生成。v2 以设计原则为主轴，区分评估边界、实际覆盖、问题影响和证据置信度。

## 目录

- 顶层字段
- coverage
- 六轴覆盖
- finding
- summary 与 verdict
- 正式示例

## 顶层字段

| 字段 | 约束 |
|---|---|
| `schema_version` | 固定为 `2` |
| `module` / `analyzed_at` | kebab-case / `YYYY-MM-DD` |
| `language` | `JVM` 或 `C++` |
| `scope` | `root_paths`、`responsibility`、`structure_summary` |
| `coverage` | 见下文；不得再用一个数组混淆范围与精读覆盖 |
| `analysis` | 取证 backend、聚焦策略、Git 使用和 omissions |
| `design_principle_coverage` | 六轴逐项结论 |
| `conventions_fed` / `convention_rules` | 用户手工输入的项目规约 |
| `known_gaps` | 影响结论的证据缺口 |
| `no_go_threshold` | 正整数，默认 1 |
| `summary` | 严重度计数、confirmed critical 数和 verdict |
| `architecture_readability` | `{overall, rationale}`，由六轴综合得出 |
| `findings` | 唯一结构问题数组；健康报告允许 `[]` |

## coverage

```json
{
  "scope_files": ["src/OrderService.java"],
  "indexed_files": ["src/OrderService.java"],
  "inspected_files": ["src/OrderService.java"],
  "semantic_resolved_files": ["src/OrderService.java"],
  "history_available": false,
  "sufficient_for_verdict": true,
  "gaps": ["未使用 Git 历史，变化隔离结论受限。"]
}
```

四个文件数组都必须是 `scope_files` 的子集；证据文件必须属于 `scope_files`。`sufficient_for_verdict=false` 时，若没有已确认 critical，verdict 必须为 `inconclusive`。

## 六轴覆盖

键固定为：

- `complexity-management`
- `responsibility-cohesion`
- `coupling-dependency-direction`
- `information-hiding`
- `abstraction-consistency`
- `change-isolation`

每轴结构：

```json
{
  "status": "concern",
  "conclusion": "订单与促销形成包级循环。",
  "evidence": [{"file": "src/OrderService.java", "line": 42, "note": "depends on PromotionService"}]
}
```

状态只能为 `concern`、`no-material-concern`、`inconclusive`。`concern` 必须有证据且至少被一个 finding 的 `principles_violated` 引用；无相关 finding 时不得写 `concern`。

## finding

```json
{
  "id": "FINDING-D01",
  "axis": "design",
  "category": "circular-dependency",
  "severity": "critical",
  "confidence": "confirmed",
  "title": "order 与 promotion 包级循环依赖",
  "evidence": [{"file": "src/OrderService.java", "line": 42, "note": "depends on PromotionService"}],
  "principles_violated": ["coupling-dependency-direction"],
  "convention_rule_ids": [],
  "impact": "两个包无法独立演进。",
  "severity_basis": "包级依赖环阻塞拆分。",
  "improvement": "抽取稳定边界或反转其中一条依赖。",
  "fix_cost": "high",
  "priority": "P1",
  "priority_basis": "它是其他拆分工作的先决条件。"
}
```

- `axis`: `design` 或 `convention`；id 分别用 `FINDING-Dnn` / `FINDING-Cnn`。
- `confidence`: `confirmed`、`probable`、`hypothesis`。
- `principles_violated`: design finding 非空；只能引用六轴键。
- `convention_rule_ids`: 可为空；非空时必须引用已声明规约。
- 同一结构问题同时违反通用原则和项目规约时，只写一条 design finding，并同时填写两组 id，禁止复制一条 convention finding。
- convention-only finding 可以不含通用原则，但必须至少引用一条规约。
- 其余字段继续要求 evidence、impact、severity_basis、improvement、fix_cost、priority、priority_basis。

## summary 与 verdict

```json
{
  "critical": 1,
  "major": 0,
  "minor": 0,
  "confirmed_critical": 1,
  "verdict": "no-go"
}
```

判定顺序：

1. `confirmed_critical >= no_go_threshold` → `no-go`；
2. 否则 `coverage.sufficient_for_verdict=false` → `inconclusive`；
3. 否则 → `go`。

严重度表示问题若成立的架构影响，confidence 表示证据强度；不得因证据弱而把潜在影响偷偷降级。

## 正式示例

- `2026-06-20-example-*`：JVM no-go。
- `2026-08-20-cpp-player-*`：C++ 架构依赖问题。
- `2026-08-20-healthy-order-*`：六轴无重大 concern 的健康 go。
- `2026-08-20-convention-api-*`：原则与项目规约合并为一条结构 finding。

普通执行不要加载示例；只在契约排错或对应分支实现时读取。
