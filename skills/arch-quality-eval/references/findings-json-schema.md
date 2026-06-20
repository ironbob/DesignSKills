# findings.json Schema —— 机器可判的发现契约源

> 配合 `arch-quality-eval` 的 Checklist 第 8 步使用。`findings.json` 是**唯一事实源**：它把「发现了什么架构问题、严重到什么程度、证据在哪、违反了哪条原理/规约、怎么改、先改哪个」结构化成机器可判的契约，`report.md` 是它的渲染、`validate_findings.py`/`validate_contract.py` 对它做强校验。两者必须一致。

## 设计原则

1. **契约即源** —— `findings.json` 先于 `report.md` 定稿；`report.md` 的计数、verdict、id 都从它派生并对账。
2. **每条发现可定位** —— 必须挂 `evidence`（file:line / 类 / 函数 / 依赖边）；定位不到的标 `unconfirmed: true` 并在 report「已知缺口」登记，**禁止编造证据**。
3. **每条发现可解释** —— `severity` 带分级依据（不是主观打分），`smell` 轴必须点名违反的**通用设计原理**、`convention` 轴必须点名违反的**用户规约 id**。
4. **三轴分清** —— `axis` ∈ `smell`（架构坏味道，模块 B）/ `readability`（架构可读性，模块 C）/ `convention`（项目规约违规，模块 B-P1，仅当喂入规约）。

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `module` | string | ✅ | 模块/子系统名（kebab-case），与 report frontmatter 一致 |
| `analyzed_at` | string | ✅ | 分析日期 `YYYY-MM-DD` |
| `language` | string | ✅ | `JVM` 或 `C++`（C++ 须同时 `cpp_limitation_noted: true`） |
| `cpp_limitation_noted` | bool | C++ 必填 | C++ 须为 `true`（已显式标注结构/依赖分析能力受限）；JVM 时省略或 `false` |
| `covered_files` | string[] | ✅ | 本次评估覆盖的文件/包集合，**非空**（模块 A 边界，显式声明优于推断） |
| `conventions_fed` | bool | ✅ | 是否喂入了用户项目规约 |
| `convention_rules` | object[] | 喂入时必填 | 喂入的规约清单，每项 `{id, rule}`（id 是 finding 回链的 join key） |
| `no_go_threshold` | int | ✅ | critical 数 ≥ 此值 → `no-go`，默认 `1` |
| `summary` | object | ✅ | `{critical, major, minor, verdict}`，各级计数 = findings 实际统计；`verdict` ∈ `go`/`no-go` |
| `readability` | object | ✅ | 可读性四轴各一句结论（详见下） |
| `findings` | object[] | ✅ | 发现清单，**非空**（详见下） |

## readability 字段（架构可读性四轴，模块 C）

每轴一段结论 + 至少一个证据锚点；结论**只评架构层可读性**，不掺 lint 能查的代码风格（缩进/命名格式/空行）。

| 字段 | 评什么 |
|------|--------|
| `responsibility_clarity` | 模块/包/类职责是否一眼可懂、是否有职责混杂 |
| `dependency_understandability` | 依赖关系是否可理解（依赖谁、为何依赖、方向是否合理） |
| `naming_expressiveness` | 命名是否表意（**语义层**：包/类/模块名是否反映其职责，**非**命名格式规范） |
| `layering_clarity` | 分层是否清晰（层边界、依赖方向、是否穿透） |

> 若某一轴在 C++ 上因结构信息受限无法充分判断，在该轴结论里说明「C++ 结构分析受限，判断保守」，并把该限制记进 report「已知缺口」。

## finding 字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 稳定 id，格式 `FINDING-<AXIS><NN>`：`S`=smell / `R`=readability / `C`=convention，如 `FINDING-S01`、`FINDING-C03`。**全文件唯一** |
| `axis` | string | ✅ | `smell` / `readability` / `convention` |
| `category` | string | ✅ | 坏味道/可读性类别（见 `arch-smells.md` / `readability-assessment.md` 枚举；convention 用 `convention-violation`） |
| `severity` | string | ✅ | `critical` / `major` / `minor`（判定见 `severity-and-priority.md`） |
| `title` | string | ✅ | 一句话标题 |
| `evidence` | object[] | ✅ | 证据清单，**非空**，每项 `{file, line, note}`（line 可缺省表示类/包级证据） |
| `principle_violated` | string | `axis==smell` 必填 | 违反的**通用设计原理**（高内聚低耦合 / 单向依赖 / 依赖倒置 / 稳定依赖 / 分层不穿透 / 接口隔离 / 信息隐藏 …）；禁空泛 |
| `convention_violated` | string | `axis==convention` 必填 | 违反的**用户规约 id**（指向 `convention_rules[].id`） |
| `impact` | string | ✅ | 这条问题带来什么后果（变更成本/风险/可维护性） |
| `improvement` | string | ✅ | 改进方向（**不写完整重构方案**，只指方向；完整重构方案超出本 skill 范围） |
| `fix_cost` | string | ✅ | `low` / `medium` / `high` |
| `priority` | string | ✅ | `P1` / `P2` / `P3`（排序依据见 `severity-and-priority.md`） |
| `unconfirmed` | bool | ✅ | 是否未在代码直接证实；`true` 时 report「已知缺口」须有对应登记 |

## 校验要点（对应脚本）

- `validate_findings.py`：schema/枚举/必填/唯一 id/计数一致/verdict ⇔ critical 阈值/smell 必有原理、convention 必有规约 id。
- `validate_contract.py`：findings.json 每个 id 在 report.md 出现；report 的 critical/major/minor 计数与 verdict 与 json 对齐；covered_files/conventions_fed 一致。

## 完整示例（节选）

```json
{
  "module": "order-service",
  "analyzed_at": "2026-06-20",
  "language": "JVM",
  "covered_files": [
    "src/main/java/com/x/order/OrderService.java",
    "src/main/java/com/x/order/OrderController.java",
    "src/main/java/com/x/promotion/PromotionService.java"
  ],
  "conventions_fed": false,
  "convention_rules": [],
  "no_go_threshold": 1,
  "summary": {"critical": 1, "major": 2, "minor": 1, "verdict": "no-go"},
  "readability": {
    "responsibility_clarity": "OrderService 混合下单/退款/促销三职责，职责边界模糊（OrderService.java:1）",
    "dependency_understandability": "order→promotion 反向依赖，依赖方向不可理解（OrderService.java:42）",
    "naming_expressiveness": "OrderManager / OrderHelper 命名不表意，无法反映职责（OrderManager.java:1）",
    "layering_clarity": "Controller 直接调 Dao，穿透 Service 层（OrderController.java:33）"
  },
  "findings": [
    {
      "id": "FINDING-S01",
      "axis": "smell",
      "category": "circular-dependency",
      "severity": "critical",
      "title": "order 与 promotion 包级循环依赖",
      "evidence": [
        {"file": "src/main/java/com/x/order/OrderService.java", "line": 42, "note": "order 包 import promotion.PromotionService"},
        {"file": "src/main/java/com/x/promotion/PromotionService.java", "line": 18, "note": "promotion 包 import order.OrderRepository"}
      ],
      "principle_violated": "单向依赖原则",
      "impact": "两个包无法独立编译/部署/演进，任一改动相互阻塞，是重构的主要阻塞点",
      "improvement": "抽取共用领域模型到独立包，或用事件/接口反转依赖方向（具体方案留重构阶段定）",
      "fix_cost": "high",
      "priority": "P1",
      "unconfirmed": false
    }
  ]
}
```
