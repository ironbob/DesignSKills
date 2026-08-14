# 设计契约 schema：`design-contract.json`

> 配合 Checklist 第 5/8 步。`design-contract.json` 是机器契约源；架构文档是人读渲染，`validate_gate.py` 做交叉对账。
>
> 内部结构由 `scripts/validate_contract.py` 做 schema/一致性烟测；文件、依赖、流程、日志与验证证据由 `scripts/validate_gate.py` 的四门辅助检查。本文档是字段表 + 示例。

---

## 一、顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `feature` | string | ✅ | feature 名（kebab-case，用于文件名前缀，如 `order-create`） |
| `title` | string | ✅ | 人读标题（如「订单创建」） |
| `stack` | string | ✅ | 技术栈，枚举 `JVM` / `C++` / `FastAPI+Vue` / `Swift/iOS` |
| `analyzed_at` | string | ✅ | 日期 `YYYY-MM-DD` |
| `existing_alignment` | object | ✅ | 模块 A：现有架构风格对齐（见 §二） |
| `design_decision` | object | ✅ | 设计强度、质量属性、候选方案、选型、风险 spike 与评审（见 §二-A） |
| `ui_architecture` | object | UI feature 必填 | UI 框架、现有/目标模式、状态管理、MVVM 适用性、迁移影响与确认（见 §二-B） |
| `roles` | array | ✅ | 模块 B 确认的角色清单（见 §三） |
| `interfaces` | array | ✅ | 编码前关键接口、数据、不变量与失败契约（见 §三-A） |
| `design_contract_checks` | array | ✅ | 模块 C 设计契约 checklist 条目（见 §四）；至少 1 条 |
| `business_process` | array | ✅ | 业务流程步骤（见 §五）；确无跨角色流程时可空 `[]`，并在架构文档说明 |
| `logging_standard` | object | ✅ | 模块 C 日志规范（见 §六） |
| `verification` | object | ✅ | 实际执行的测试/检查、覆盖映射和未验证项（见 §六-A） |
| `summary` | object | ✅ | 计数汇总（见 §七） |
| `gate` | object | ✅ | 模块 E 四道门结论（见 §八） |
| `open_questions` | array | ⬜ | 未决问题（问题 + 影响 + 后续阶段） |

---

## 二、`existing_alignment`（模块 A）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `recognized_style` | string | ✅ | 陈述仓库现有架构风格（分层/命名/日志习惯），如「Spring Boot 三层 + SLF4J，包按 `com.x.<域>` 分」 |
| `new_code_follows` | string | ✅ | 新代码如何沿用（包结构/命名/日志库与现有一致），如「沿用三层 + SLF4J，订单域放 `com.x.order`」 |

> 这是「对齐现有、不另起炉灶」的显式声明（PRD 模块 A P0 验收）。

### 二-A、`design_decision`（构造期架构决策）

| 字段 | 约束 |
|---|---|
| `profile` | `light` / `standard` / `high_risk` |
| `quality_attributes[]` | 非空；每项含 `name`、`priority`(`high/medium/low`)、`scenario`、`acceptance` |
| `candidates[]` | 非空；每项含唯一 `id`(`ALT-<n>`)、`summary`、非空 `strengths/weaknesses/risks` |
| `selected_id` | 必须解析到某候选 |
| `selection_reason` | 引用质量属性与仓库约束的具体取舍 |
| `top_down_check` | 从流程/边界推导角色的结论 |
| `bottom_up_check` | 从现有代码/框架/数据反查落地性的结论 |
| `risk_spikes[]` | 每项含 `question/method/result/status`；`status` 为 `passed/failed/inconclusive` |
| `review` | `mode`(`self/user/peer/independent`) + `reviewer/findings/disposition` |

`standard/high_risk` 至少 2 个候选；`high_risk` 至少 1 个 spike，且 review.mode 必须是 `user` 或 `peer`。`light` 可只有一个候选并自审。

### 二-B、`ui_architecture`（所有语言的 UI feature 条件必填）

```json
"ui_architecture": {
  "framework": "SwiftUI",
  "current_patterns": ["MVC", "Coordinator"],
  "target_patterns": ["MVVM", "Coordinator"],
  "state_management": "Observation @Observable; screen state owned by @MainActor ViewModel",
  "view_model_policy": "required",
  "mvvm_suitability": "suitable",
  "migration_impact": "medium",
  "impact_scope": ["OrderScreen", "OrderCoordinator"],
  "migration_confirmation": "not_required",
  "decision_reason": "Screen has asynchronous loading, retry, selection and navigation; View stays rendering-only"
}
```

| 字段 | 约束 |
|---|---|
| `framework` | 非空；写真实框架，如 `SwiftUI` / `Android Compose` / `Vue 3` / `Qt QML` |
| `current_patterns[]` | 非空且唯一，取 `MVVM` / `MVC` / `MVP` / `Coordinator` / `Clean/VIP` / `TCA` / `Redux/Store` / `Direct View` / `Other` |
| `target_patterns[]` | 非空且唯一，枚举同上；表达本 feature 编码后的模式 |
| `state_management` | 单一事实源、状态工具与所有者的明确说明 |
| `view_model_policy` | `required` / `optional` / `not_used` |
| `mvvm_suitability` | `suitable` / `not_suitable` / `already_used` |
| `migration_impact` | `none` / `low` / `medium` / `high` |
| `impact_scope[]` | 受影响的页面、模块、公共接口、状态/导航/组装与测试；无影响可空 `[]` |
| `migration_confirmation` | `not_required` / `user_confirmed` / `pending` |
| `decision_reason` | 为什么采用或不采用 MVVM，必须结合现有工程和 feature 复杂度 |

- `target_patterns` 含 `MVVM` 时，`view_model_policy` 必须为 `required`，并至少存在一个 `layer=view_model` 的角色。
- 存在 ViewModel 角色时目标模式必须声明 `MVVM`；不采用 MVVM 时不得创建名义 ViewModel 角色。
- `mvvm_suitability=suitable|already_used` 时优先 MVVM；若目标仍不采用，校验器告警并要求 `decision_reason` 说明具体取舍。
- 若 `current_patterns` 不含 MVVM、`target_patterns` 含 MVVM 且 `migration_impact=high`，`design_decision.profile` 必须为 `high_risk`，且 `migration_confirmation` 必须为 `user_confirmed`；`pending` 时不得编码。
- 非高影响或未引入 MVVM 时通常填 `not_required`；纯展示页可用 `Direct View + not_used`，但仍要说明状态与依赖边界。

---

## 三、`roles[]`（模块 B 核心 — 角色清单）

**这是整个契约的心脏。** 每个角色一个对象：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | 稳定 id，正则 `^ROLE-[LD]\d+$`：`ROLE-L01`（**L**=分层角色）/ `ROLE-D01`（**D**=领域角色）。id 全局唯一；**前缀编码 role_kind**（脚本校验前缀⇒role_kind 一致） |
| `name` | string | ✅ | 角色名（代码里的类/模块名，如 `OrderController` / `OrderAggregate`） |
| `role_kind` | string | ✅ | 枚举 `layer`（分层角色）/ `domain`（领域角色）。须与 id 前缀一致（L⇒layer, D⇒domain） |
| `layer` | string | ✅ | 所在层，枚举 `controller` / `service` / `repository` / `domain` / `infrastructure` / `facade` / `router` / `view` / `view_model` / `application` / `coordinator` / `composition` / `mapper` / `store` / `util` |
| `domain_role` | string \| null | ✅ | 领域角色类型，枚举 `aggregate` / `entity` / `value_object` / `domain_service` / `domain_event` / `null`（分层角色通常 null；领域角色必填） |
| `responsibility` | string | ✅ | 一句话职责（单一职责；动词开头，如「接收下单请求、校验入参、编排流程」） |
| `hidden_secret` | string | ✅ | 该角色隐藏的易变/困难设计决定；如「HTTP 请求/响应映射」 |
| `change_triggers` | array | ✅ | 应主要局限在该角色的变化来源；非空 |
| `data_owned` | string | ✅ | 拥有/维护的数据或状态；无持久状态也要明确说明 |
| `depends_on` | array | ✅ | 依赖的其他 role id（依赖方向依据，如 `["ROLE-L02"]`）；无依赖用 `[]` |
| `industry_basis` | string | ✅ | **业界做法依据**（PRD 强制）：如「MVC Controller（Spring @RestController）」/「DDD 聚合根，封装订单不变量」 |
| `design_principles` | array | ✅ | **所依据的设计原则**（PRD 强制）：从规范集取（见 §九），如 `["SRP", "DIP"]` |
| `code_units` | array | ✅ | 对应代码文件（仓库根相对路径，如 `src/main/java/com/x/order/OrderController.java`）；架构门校验**文件存在** |

> **分层角色 + 领域角色两类都要过一遍**：若该需求只用一类，在角色清单或 `open_questions` 说明理由，不静默漏。

### 三-A、`interfaces[]`（编码前最小接口契约）

每个关键跨角色调用一个对象。仅 `light` 且单角色、确实没有跨角色调用时可用空数组，并在架构文档说明。

| 字段 | 约束 |
|---|---|
| `id` | 唯一 `IFC-<n>` |
| `name` | 代码中的关键调用名，如 `OrderService.create` |
| `provider` | 一个有效 role id |
| `consumers[]` | 非空、有效 role id |
| `input` / `output` | 非空，说明类型和语义 |
| `preconditions[]` / `postconditions[]` / `invariants[]` | 均为非空字符串数组；没有额外条件时写明确的 `none` |
| `errors[]` | 非空；说明错误类型、传播/转换和调用方责任 |
| `data_ownership` | 数据所有权、可变性和生命周期 |
| `transaction` / `concurrency` | 事务、幂等、线程/actor、取消边界；不适用写 `not_applicable` |

---

## 四、`design_contract_checks[]`（模块 C — 软引导 checklist）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | `^DC-\d+$`，如 `DC-1` |
| `item` | string | ✅ | checklist 条目（编码时对照），如「依赖方向：controller→service→repository，不反向」 |
| `principle` | string | ✅ | 该条对应的设计原则（从 §九 规范集），如 `DIP` |
| `role_scope` | array | ⬜ | 该条约束的角色 id（可空 = 全局） |

> 这是**软引导**（对照提醒），不是逐角色硬门禁；最终复核看架构原则与代码设计原则是否真实落到代码，模块 E 脚本只提供结构证据。

---

## 五、`business_process[]`（模块 B P1 / 模块 D / 模块 E 覆盖门）

业务流程主线，每步一个对象：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `step` | int | ✅ | 步骤序号（从 1，递增） |
| `name` | string | ✅ | 步骤名（如「接收下单请求」） |
| `roles` | array | ✅ | 参与本步的 role id（须有效），如 `["ROLE-L01"]` |
| `code_refs` | array | ✅ | 本步代码落点（仓库根相对路径，可带 `:方法`）；覆盖门校验文件与符号文本近似存在 |
| `doc_ref` | string | ✅ | 本步在架构文档的体现位置（如「业务流程图-步骤1」）；覆盖门交叉对账 |
| `exception` | string \| null | ✅ | 本步异常/分支（至少标注；无则 `null`），如「库存不足 → 抛 InsufficientStockException」 |

> 覆盖门要求：流程每步 ↔ 代码文件/符号 ↔ 文档真实引用三者对得上。

---

## 六、`logging_standard`（模块 C / 日志门）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `library` | string | ✅ | 按栈日志库，如 `SLF4J/Logback` / `logging/loguru` / `spdlog` / `OSLog.Logger` |
| `key_nodes_instrumented` | array | ✅ | 已打点的关键节点，从规范集 `["入口","出口","异常","外部调用"]` 取 |

### 六-A、`verification`（构造质量证据）

| 字段 | 约束 |
|---|---|
| `commands[]` | 实际执行记录；每项含非空 `command/result/evidence`，`status` 为 `passed/failed/skipped` |
| `checks[]` | 质量属性、不变量或异常路径到证据的映射；每项含 `target/method/evidence/status`，method 为 `existing_test/new_test/static_check/manual_review` |
| `unverified[]` | 无法验证的项目；每项含 `item/impact/follow_up`；无则 `[]` |

存在 `failed` 命令或 check 时不得 `gate.verification=go`。存在 `skipped/unverified` 时必须在 `gate.notes` 说明置信度影响。

---

## 七、`summary`（计数汇总 — 脚本校验与实际一致）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `roles_count` | int | ✅ | = `roles.length` |
| `interfaces_count` | int | ✅ | = `interfaces.length` |
| `process_steps` | int | ✅ | = `business_process.length` |
| `verification_checks` | int | ✅ | = `verification.checks.length` |
| `layer_roles` | int | ✅ | = role_kind=layer 的数量 |
| `domain_roles` | int | ✅ | = role_kind=domain 的数量 |

---

## 八、`gate`（模块 E — 四道门辅助证据 + 原则复核）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `architecture` | string | ✅ | 架构门结构证据，枚举 `go` / `no-go` |
| `logging` | string | ✅ | 日志门结构证据，枚举 `go` / `no-go` |
| `coverage` | string | ✅ | 覆盖门结构证据，枚举 `go` / `no-go` |
| `verification` | string | ✅ | 验证命令与关键检查证据，枚举 `go` / `no-go` |
| `verdict` | string | ✅ | 四门证据的汇总结论，枚举 `go` / `no-go`；必须与四门一致 |
| `issues` | array | ✅ | 问题清单（见下）；全 go 时可空 `[]` |
| `notes` | string | ✅ | 原则复核与校验诚实说明：哪些是真设计问题，哪些是脚本近似能力限制，语义项如何登记缺口 |

### `gate.issues[]`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `gate` | string | ✅ | 枚举 `architecture` / `logging` / `coverage` / `verification` |
| `severity` | string | ✅ | 枚举 `critical` / `major` / `minor` |
| `role_or_step` | string | ✅ | 挂点的 role id 或 step 序号（如 `ROLE-L02` / `step:2`） |
| `problem` | string | ✅ | 问题描述 |
| `evidence` | string | ✅ | 证据（文件:行 / 方法 / 或「辅助校验未覆盖（语义项）」） |

> 结构性 no-go 通常应修；若判断为脚本近似能力限制，不要机械调阈值，需在 `notes` 和架构文档「已知缺口」说明原因、影响和后续处理。

---

## 九、设计原则规范集（`design_principles` 取值）

`roles[].design_principles` 与 `design_contract_checks[].principle` 从此集取（脚本对未知值**告警**而非报错——团队可能引用其他原则）：

- **SOLID**：`SRP` / `OCP` / `LSP` / `ISP` / `DIP`
- **DDD**：`aggregate` / `entity` / `value_object` / `domain_service` / `domain_event` / `bounded_context` / `context_mapping`
- **通用**：`high_cohesion_low_coupling`（高内聚低耦合）/ `dependency_direction`（依赖方向）/ `separation_of_concerns`（关注点分离）/ `tell_dont_ask`（Tell-Don't-Ask）/ `information_hiding` / `minimize_complexity` / `defensive_design`

> 详见 `references/design-principles.md`。

---

## 十、字段片段（非完整契约）

下面字段片段只说明基本形状，不可直接送入当前校验器。可执行的唯一完整示例见 `examples/2026-06-28-example-design-contract.json`。

```json
{
  "feature": "order-create",
  "title": "订单创建",
  "stack": "JVM",
  "analyzed_at": "2026-06-28",
  "existing_alignment": {
    "recognized_style": "Spring Boot 三层（controller/service/repository）+ SLF4J，包按 com.x.<域> 分",
    "new_code_follows": "沿用三层 + SLF4J，订单域放 com.x.order"
  },
  "roles": [
    {
      "id": "ROLE-L01",
      "name": "OrderController",
      "role_kind": "layer",
      "layer": "controller",
      "domain_role": null,
      "responsibility": "接收创建订单 HTTP 请求、校验入参、编排下单流程、返回结果",
      "depends_on": ["ROLE-L02"],
      "industry_basis": "MVC Controller（Spring @RestController，只做协议适配与编排）",
      "design_principles": ["SRP", "DIP"],
      "code_units": ["src/main/java/com/x/order/OrderController.java"]
    },
    {
      "id": "ROLE-D01",
      "name": "OrderAggregate",
      "role_kind": "domain",
      "layer": "domain",
      "domain_role": "aggregate",
      "responsibility": "封装订单聚合根，维护下单不变量（库存校验、金额一致性）",
      "depends_on": [],
      "industry_basis": "DDD 聚合根，一致性边界内封装业务规则",
      "design_principles": ["aggregate", "high_cohesion_low_coupling"],
      "code_units": ["src/main/java/com/x/order/OrderAggregate.java"]
    }
  ],
  "design_contract_checks": [
    { "id": "DC-1", "item": "依赖方向 controller→service→repository，不反向", "principle": "dependency_direction", "role_scope": ["ROLE-L01", "ROLE-L02", "ROLE-L03"] }
  ],
  "business_process": [
    {
      "step": 1,
      "name": "接收下单请求",
      "roles": ["ROLE-L01"],
      "code_refs": ["src/main/java/com/x/order/OrderController.java:createOrder"],
      "doc_ref": "业务流程图-步骤1",
      "exception": null
    },
    {
      "step": 2,
      "name": "校验库存并创建订单聚合",
      "roles": ["ROLE-L02", "ROLE-D01"],
      "code_refs": ["src/main/java/com/x/order/OrderService.java:create"],
      "doc_ref": "业务流程图-步骤2",
      "exception": "库存不足 → 抛 InsufficientStockException"
    }
  ],
  "logging_standard": {
    "library": "SLF4J/Logback",
    "key_nodes_instrumented": ["入口", "出口", "异常", "外部调用"]
  },
  "summary": { "roles_count": 4, "process_steps": 2, "layer_roles": 3, "domain_roles": 1 },
  "gate": {
    "architecture": "go",
    "logging": "go",
    "coverage": "go",
    "verdict": "go",
    "issues": [],
    "notes": "生成侧结构性自检（角色↔文件存在、日志关键字覆盖、流程↔代码↔文档）+ LLM 语义自检混合"
  }
}
```
