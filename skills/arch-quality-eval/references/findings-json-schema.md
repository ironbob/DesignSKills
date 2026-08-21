# findings.json 契约

`findings.json` 是唯一事实源；`report.md` 必须由 `render_report.py` 生成。先写并校验 JSON，不要并行写两份事实。

## 顶层字段

| 字段 | 约束 |
|---|---|
| `module` | kebab-case 模块名 |
| `title` | 可选的人读标题 |
| `analyzed_at` | `YYYY-MM-DD` |
| `language` | `JVM` 或 `C++` |
| `cpp_limitation_noted` | C++ 必须为 `true` |
| `scope` | 见下文；保存已确认范围基线 |
| `covered_files` | 非空源文件数组；证据文件必须属于此集合 |
| `conventions_fed` | boolean |
| `convention_rules` | `{id, rule}[]`；未喂入时为空 |
| `analysis` | 取证模式、聚焦策略、Git 使用和未覆盖项 |
| `core_smell_coverage` | 核心五类逐项 `detected` / `not-detected` |
| `known_gaps` | 未确认项和能力限制数组 |
| `no_go_threshold` | 正整数，默认 1 |
| `summary` | `{critical, major, minor, verdict}` |
| `readability` | 四轴结论 + `overall` |
| `findings` | finding 数组；健康报告允许空数组 |

### scope

```json
{
  "root_paths": ["src/main/java/com/x/order"],
  "responsibility": "负责订单创建与退款。",
  "structure_summary": "JVM 包 com.x.order，按 controller/service/repository 分层。"
}
```

### analysis

```json
{
  "symbol_mode": "LSP",
  "focus_strategy": "先读依赖中枢，再抽样非热点包。",
  "git_history_used": true,
  "omissions": []
}
```

`symbol_mode` 只能为 `LSP`、`clang-ast` 或 `text-search`。C++ 使用 compile database + clang AST 时填 `clang-ast`；Git 不可用时设 `false`，并在 `omissions` 说明历史型坏味道覆盖限制。

### core_smell_coverage

键固定为：

```json
{
  "circular-dependency": "detected",
  "god-class-or-package": "not-detected",
  "cross-layer": "not-detected",
  "shotgun-surgery": "not-detected",
  "inappropriate-exposure": "not-detected"
}
```

状态必须与 findings 的实际 category 一致；不能用“未写 finding”冒充“已检查”。

### readability

必须包含：

- `responsibility_clarity`
- `dependency_understandability`
- `naming_expressiveness`
- `layering_clarity`
- `overall`

四轴结论写架构语义并带证据锚点；不要写 lint 问题。

## finding 字段

| 字段 | 约束 |
|---|---|
| `id` | `FINDING-S01` / `FINDING-R01` / `FINDING-C01`；前缀与 axis 一致且唯一 |
| `axis` | `smell` / `readability` / `convention` |
| `category` | 坏味道、可读性类别；规约统一为 `convention-violation` |
| `severity` | `critical` / `major` / `minor` |
| `title` | 一句话标题 |
| `evidence` | 非空 `{file, line?, note}[]`；file 属于 covered_files |
| `principle_violated` | smell/readability 必填 |
| `convention_violated` | convention 必填，指向 convention rule id |
| `impact` | 可维护性、变更成本或风险影响 |
| `severity_basis` | 用爆炸半径、阻塞性、可增量性、证据强度解释级别 |
| `improvement` | 只给方向，不写完整设计 |
| `fix_cost` | `low` / `medium` / `high` |
| `priority` | `P1` / `P2` / `P3` |
| `priority_basis` | 用影响面、阻塞、成本和先决关系解释排序 |
| `unconfirmed` | boolean；为 true 时必须在 known_gaps 登记 |

示例 finding：

```json
{
  "id": "FINDING-S01",
  "axis": "smell",
  "category": "circular-dependency",
  "severity": "critical",
  "title": "order 与 promotion 包级循环依赖",
  "evidence": [
    {"file": "src/OrderService.java", "line": 42, "note": "import promotion.PromotionService"},
    {"file": "src/PromotionService.java", "line": 18, "note": "import order.OrderRepository"}
  ],
  "principle_violated": "单向依赖原则",
  "impact": "两个包无法独立演进。",
  "severity_basis": "包级依赖环阻塞后续拆分，因此为 critical。",
  "improvement": "抽取共享抽象或反转其中一条依赖。",
  "fix_cost": "high",
  "priority": "P1",
  "priority_basis": "它是其他职责拆分的先决条件。",
  "unconfirmed": false
}
```

## 一致性规则

- `summary` 计数必须等于 findings 实际计数。
- `verdict=no-go` 当且仅当 critical 数不小于 `no_go_threshold`。
- `conventions_fed=false` 时禁止 convention finding。
- `unconfirmed` 数量不得超过 `known_gaps` 可解释的数量。
- 先运行 `validate_findings.py` 和 `validate_evidence.py`；通过后再运行 renderer。

## 正式示例

- `2026-06-20-example-*`：JVM no-go 正向示例。
- `2026-08-20-cpp-player-*`：C++ compile database + clang AST 示例。
- `2026-08-20-healthy-order-*`：`findings: []` 的健康 go 示例。
- `2026-08-20-convention-api-*`：通用 smell 与用户规约 finding 同源并存示例。

每个前缀均包含 `findings.json` 与 renderer 生成的 `report.md`，fixture 位于 `examples/fixtures/<module>/`。普通执行不要加载完整示例，只有契约排错或对应分支实现时读取。
