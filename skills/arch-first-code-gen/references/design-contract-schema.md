# 设计契约 schema：`design-contract.json`

> 配合 `arch-first-code-gen` 的 Checklist 第 7 步。`design-contract.json` 是**机器契约源 / 唯一事实源**——角色、职责、依赖、业界依据、设计原则、代码单元、业务流程、复核结论全在这里。架构文档 `<feature>-arch.md` 是它的**渲染**；`validate_gate.py` 可辅助做 json↔md 对账。
>
> 内部结构由 `scripts/validate_contract.py` 做 schema/一致性烟测；文件存在性 + 三门结构证据由 `scripts/validate_gate.py` 辅助检查。本文档是字段表 + 示例。

---

## 一、顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `feature` | string | ✅ | feature 名（kebab-case，用于文件名前缀，如 `order-create`） |
| `title` | string | ✅ | 人读标题（如「订单创建」） |
| `stack` | string | ✅ | 技术栈，枚举 `JVM` / `C++` / `FastAPI+Vue` |
| `analyzed_at` | string | ✅ | 日期 `YYYY-MM-DD` |
| `existing_alignment` | object | ✅ | 模块 A：现有架构风格对齐（见 §二） |
| `roles` | array | ✅ | 模块 B 确认的角色清单（见 §三） |
| `design_contract_checks` | array | ✅ | 模块 C 设计契约 checklist 条目（见 §四）；可空 `[]`（简单需求） |
| `business_process` | array | ✅ | 业务流程步骤（见 §五）；可空 `[]`（纯 CRUD 无流程时，但需在 doc_ref 说明） |
| `logging_standard` | object | ✅ | 模块 C 日志规范（见 §六） |
| `summary` | object | ✅ | 计数汇总（见 §七） |
| `gate` | object | ✅ | 模块 E 三道门结论（见 §八） |
| `open_questions` | array | ⬜ | 未决问题（问题 + 影响 + 后续阶段） |

---

## 二、`existing_alignment`（模块 A）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `recognized_style` | string | ✅ | 陈述仓库现有架构风格（分层/命名/日志习惯），如「Spring Boot 三层 + SLF4J，包按 `com.x.<域>` 分」 |
| `new_code_follows` | string | ✅ | 新代码如何沿用（包结构/命名/日志库与现有一致），如「沿用三层 + SLF4J，订单域放 `com.x.order`」 |

> 这是「对齐现有、不另起炉灶」的显式声明（PRD 模块 A P0 验收）。

---

## 三、`roles[]`（模块 B 核心 — 角色清单）

**这是整个契约的心脏。** 每个角色一个对象：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | ✅ | 稳定 id，正则 `^ROLE-[LD]\d+$`：`ROLE-L01`（**L**=分层角色）/ `ROLE-D01`（**D**=领域角色）。id 全局唯一；**前缀编码 role_kind**（脚本校验前缀⇒role_kind 一致） |
| `name` | string | ✅ | 角色名（代码里的类/模块名，如 `OrderController` / `OrderAggregate`） |
| `role_kind` | string | ✅ | 枚举 `layer`（分层角色）/ `domain`（领域角色）。须与 id 前缀一致（L⇒layer, D⇒domain） |
| `layer` | string | ✅ | 所在层，枚举 `controller` / `service` / `repository` / `domain` / `infrastructure` / `facade` / `router` / `view` / `store` / `util`（按栈补充） |
| `domain_role` | string \| null | ✅ | 领域角色类型，枚举 `aggregate` / `entity` / `value_object` / `domain_service` / `domain_event` / `null`（分层角色通常 null；领域角色必填） |
| `responsibility` | string | ✅ | 一句话职责（单一职责；动词开头，如「接收下单请求、校验入参、编排流程」） |
| `depends_on` | array | ✅ | 依赖的其他 role id（依赖方向依据，如 `["ROLE-L02"]`）；无依赖用 `[]` |
| `industry_basis` | string | ✅ | **业界做法依据**（PRD 强制）：如「MVC Controller（Spring @RestController）」/「DDD 聚合根，封装订单不变量」 |
| `design_principles` | array | ✅ | **所依据的设计原则**（PRD 强制）：从规范集取（见 §九），如 `["SRP", "DIP"]` |
| `code_units` | array | ✅ | 对应代码文件（仓库根相对路径，如 `src/main/java/com/x/order/OrderController.java`）；架构门校验**文件存在** |

> **分层角色 + 领域角色两类都要过一遍**：若该需求只用一类，在角色清单或 `open_questions` 说明理由，不静默漏。

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
| `code_refs` | array | ✅ | 本步代码落点（仓库根相对路径，可带 `:方法`），如 `["src/.../OrderController.java:createOrder"]`；覆盖门校验**文件存在** |
| `doc_ref` | string | ✅ | 本步在架构文档的体现位置（如「业务流程图-步骤1」）；覆盖门交叉对账 |
| `exception` | string \| null | ✅ | 本步异常/分支（至少标注；无则 `null`），如「库存不足 → 抛 InsufficientStockException」 |

> 覆盖门要求：流程每步 ↔ 代码(code_refs 文件存在) ↔ 文档(doc_ref) **三者对得上**。

---

## 六、`logging_standard`（模块 C / 日志门）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `library` | string | ✅ | 按栈日志库，如 `SLF4J/Logback` / `logging/loguru` / `spdlog` |
| `key_nodes_instrumented` | array | ✅ | 已打点的关键节点，从规范集 `["入口","出口","异常","外部调用"]` 取 |

---

## 七、`summary`（计数汇总 — 脚本校验与实际一致）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `roles_count` | int | ✅ | = `roles.length` |
| `process_steps` | int | ✅ | = `business_process.length` |
| `layer_roles` | int | ✅ | = role_kind=layer 的数量 |
| `domain_roles` | int | ✅ | = role_kind=domain 的数量 |

---

## 八、`gate`（模块 E — 三道门辅助证据 + 原则复核）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `architecture` | string | ✅ | 架构门结构证据，枚举 `go` / `no-go` |
| `logging` | string | ✅ | 日志门结构证据，枚举 `go` / `no-go` |
| `coverage` | string | ✅ | 覆盖门结构证据，枚举 `go` / `no-go` |
| `verdict` | string | ✅ | 三门结构证据的汇总结论，枚举 `go` / `no-go`；建议与三门一致，若因脚本近似误伤而不作为交付阻断，必须在 `notes` 说明 |
| `issues` | array | ✅ | 问题清单（见下）；全 go 时可空 `[]` |
| `notes` | string | ✅ | 原则复核与校验诚实说明：哪些是真设计问题，哪些是脚本近似能力限制，语义项如何登记缺口 |

### `gate.issues[]`

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `gate` | string | ✅ | 枚举 `architecture` / `logging` / `coverage` |
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
- **通用**：`high_cohesion_low_coupling`（高内聚低耦合）/ `dependency_direction`（依赖方向）/ `separation_of_concerns`（关注点分离）/ `tell_dont_ask`（Tell-Don't-Ask）

> 详见 `references/design-principles.md`。

---

## 十、端到端示例（节选 — 完整见 `examples/`）

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
