# overview.json Schema —— 机器可判的总览契约源

> 配合 `arch-overview` 的 Checklist 第 8 步使用。`overview.json` 是**唯一事实源**：它把「3 视角图的结构化定义 + 4 维评估 + 业界做法对照 + 亮点/风险」结构化成机器可判的契约，`overview.md` 是它的渲染，`validate_overview.py`/`validate_evidence.py`/`validate_contract.py` 对它做强校验。两者必须一致。

## 设计原则

1. **契约即源** —— `overview.json` 先于 `overview.md` 定稿；`overview.md` 的档位、id、覆盖集合都从它派生并对账。
2. **每条可定位** —— 图节点/边/流转步、维度评估、亮点/风险都挂 `evidence`（file:line / 包 / 模块 / 依赖边）；定位不到的标对应项 `unconfirmed`/`⚠ 未确认` 并登记 `gaps`，**禁止编造证据**。`validate_evidence.py` 轻量校验证据文件、行号、note 关键字。
3. **每维可解释** —— `grade`（优/良/中/差）带客观依据（现状 + 业界差距），非主观打分。
4. **业界对照 provenance 透明** —— 每维 `industry_practice` 必须声明 `provenance="LLM内置经验"` + `verified=false` + `further_reading`，不联网不假装权威。
5. **3 视角适用性显式** —— 每视角 `applicable` 必填；`true` 须有 `mermaid` + 非空节点/流转，`false` 须有 `reason`。

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

每个视角对象共用字段：`applicable`（bool，必填）。`applicable=true` 时须有 `mermaid`（非空字符串）+ 对应结构；`applicable=false` 时须有 `reason`（非空）。

### diagrams.layering（视角①分层/模块依赖）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `applicable` | bool | ✅ | 几乎都 true |
| `reason` | string | false 时必填 | 不适用原因 |
| `mermaid` | string | true 时必填 | `flowchart` 代码（含 subgraph 分层） |
| `nodes` | object[] | true 时必填 | 每项 `{id, label, evidence[]}`，**非空** |
| `edges` | object[] | true 时必填 | 每项 `{from, to, evidence[]}` |

### diagrams.c4（视角②C4 Container/Component）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `applicable` | bool | ✅ | |
| `reason` | string | false 时必填 | |
| `level` | string | true 时必填 | `container` 或 `component` |
| `mermaid` | string | true 时必填 | `flowchart` 代码（shape 模拟 C4） |
| `nodes` | object[] | true 时必填 | 每项 `{id, label, kind, evidence[]}`；`kind` ∈ `service`/`component`/`store`/`external`/`actor` |
| `edges` | object[] | true 时必填 | 每项 `{from, to, label?, evidence[]}` |

### diagrams.runtime（视角③运行时/数据流）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `applicable` | bool | ✅ | 纯库模块可能 false |
| `reason` | string | false 时必填 | 如「纯库模块无运行时入口」 |
| `mermaid` | string | true 时必填 | `sequenceDiagram` 或 `flowchart` 代码 |
| `flows` | object[] | true 时必填 | 每项 `{step, action, evidence[]}`，**非空**；step 为序号/标识 |

### 通用 evidence 子结构

`evidence[]` 每项：`{file, line?, note}` —— `file` 相对 repo root 或绝对路径；`line` 可缺省（表示包/模块级证据）；`note` 说明该证据指向什么。

## 校验要点（对应脚本）

- `validate_overview.py`：顶层必填/类型；`scope_level` 枚举；`languages` 非空；`language_precision.precision` 枚举；`covered_files` 非空；`overall_grade` 枚举；`dimensions` 恰好 4 条且 key 集合齐全、`grade` 枚举、`industry_practice` 5 子字段齐全且 `provenance="LLM内置经验"`/`verified=false`/`further_reading` 非空、`evidence` 非空含 file；`highlights`/`risks` id 唯一合法（HL-/RISK-）+ evidence 非空；`diagrams` 3 键齐全、`applicable` 一致性、provenance；允许 `highlights: []`/`risks: []`。
- `validate_evidence.py`：递归遍历所有 `evidence[]`（dimensions/highlights/risks/diagrams 各结构），校验文件存在、行号范围、note 关键字命中。
- `validate_contract.py`：overview.json 与 overview.md 的 `overall_grade`、4 维 grade、`covered_files`、`languages`、`scope_level` 一致；highlights/risks id 在 md 出现且无悬空。

## 完整示例（节选，完整见 examples/）

```json
{
  "target": "order-api",
  "analyzed_at": "2026-07-10",
  "scope_level": "app",
  "languages": ["Python", "TypeScript"],
  "language_precision": [
    {"language": "Python", "precision": "medium", "note": "import 规范，但动态加载标 unconfirmed"},
    {"language": "TypeScript", "precision": "high", "note": "显式 import/export，依赖边可靠"}
  ],
  "covered_files": ["backend/app/api/orders.py", "backend/app/services/order_service.py"],
  "responsibility": "处理订单的创建、查询、状态流转与异步履约",
  "overall_grade": "良",
  "dimensions": [
    {
      "key": "layering",
      "grade": "良",
      "assessment": "api/services/repository 三层清晰，依赖基本单向；个别处 repository 反向引用 service 工具",
      "industry_practice": {
        "what": "分层架构：上层依赖下层，不跨层不反向",
        "when": "职责可清晰分层的企业应用",
        "gap": "存在个别 repository→service 反向引用，分层不纯净",
        "provenance": "LLM内置经验",
        "verified": false,
        "further_reading": ["Layered Architecture", "《领域驱动设计》分层"]
      },
      "evidence": [{"file": "backend/app/repository/order_repo.py", "line": 24, "note": "import order_service.format_sku"}]
    }
  ],
  "highlights": [
    {"id": "HL-01", "title": "支付方式用策略模式扩展，新增不改既有", "dimension": "extensibility",
     "evidence": [{"file": "backend/app/services/payment/strategy.py", "line": 12, "note": "PaymentStrategy 接口 + 多实现注册"}]}
  ],
  "risks": [
    {"id": "RISK-01", "title": "订单状态机硬编码在 service，业务增长后改动易散落", "dimension": "extensibility",
     "note": "未来若状态/规则增多，集中硬编码可能演变为霰弹式修改；可考虑抽状态机/规则引擎",
     "evidence": [{"file": "backend/app/services/order_service.py", "line": 88, "note": "if/elif 状态分支"}]}
  ],
  "diagrams": {
    "layering": {
      "applicable": true, "reason": "",
      "mermaid": "flowchart TD\n  subgraph web[\"API层\"]\n    A[\"orders.py\"]\n  end\n  A --> S[\"order_service\"]\n  S --> R[\"order_repo\"]",
      "nodes": [{"id": "A", "label": "orders.py (api)", "evidence": [{"file": "backend/app/api/orders.py", "line": 1}]}],
      "edges": [{"from": "A", "to": "S", "evidence": [{"file": "backend/app/api/orders.py", "line": 17, "note": "import order_service"}]}]
    },
    "c4": {
      "applicable": true, "level": "container", "reason": "",
      "mermaid": "flowchart LR\n  U([\"用户 ext\"]) --> API[\"Order API (Python)\"]\n  API --> DB[(\"OrderDB (PostgreSQL)\")]\n  API --> MQ[(\"Kafka\")]\n  MQ --> W[\"Worker (Python)\"]\n  W --> PAY{{\"支付网关 ext\"}}",
      "nodes": [{"id": "API", "label": "Order API", "kind": "service", "evidence": [{"file": "backend/app/main.py", "line": 1}]}],
      "edges": [{"from": "API", "to": "DB", "label": "SQL", "evidence": [{"file": "backend/app/repository/order_repo.py", "line": 30}]}]
    },
    "runtime": {
      "applicable": true, "reason": "",
      "mermaid": "sequenceDiagram\n  participant C as Client\n  participant A as API\n  participant S as order_service\n  participant R as order_repo\n  C->>A: POST /orders\n  A->>S: create_order()\n  S->>R: save()\n  R-->>S: ok\n  S-->>A: 201",
      "flows": [{"step": "2", "action": "API 调 order_service.create_order", "evidence": [{"file": "backend/app/api/orders.py", "line": 20, "note": "create_order(req)"}]}]
    }
  },
  "gaps": ["Python 动态 import 的隐式依赖未完全实锤，部分边标 unconfirmed"]
}
```
