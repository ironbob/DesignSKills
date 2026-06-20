# 项目规约违规检测（模块 B-P1）

> 配合 `arch-quality-eval` 的 Checklist 第 4 步使用。**仅当用户手工喂入了项目架构规约时触发**（PRD §4-A P1 / §4-B P1）。未喂入则**整节不触发**，只跑通用准则（`arch-smells.md`）。

## 一、什么是「项目规约」

用户**手工喂入**的、本项目的架构约束，不是 skill 推断的、也不是 skill 去解析 `ARCHITECTURE.md` 得到的（PRD §5：不自动解析项目架构文档；§5：不从代码结构推断「应有架构」）。典型形态：

- **分层规则**：「Controller 只能调 Service，Service 只能调 Dao/Repository，Dao 不得反向调 Service」（层 + 允许/禁止依赖方向）。
- **模块边界**：「order 模块不得依赖 promotion 模块；共用模型放 common」「支付走 pay-gateway 模块，不得直连第三方」。
- **禁止依赖方向**：「领域层不得依赖 Web/基础设施层」「抽象层不得依赖实现层」。
- **命名/分包约定（架构语义层）**：「对外 API 必须在 `api` 包；内部实现不得对外包可见」——仅当它关乎**架构边界/暴露面**，不是代码风格。

## 二、规约的喂入格式（写进 findings.json `convention_rules`）

每条规约给一个稳定 `id`（finding 回链的 join key）：

```json
"convention_rules": [
  {"id": "CONV-L1", "rule": "Controller 只能依赖 Service，不得直接依赖 Dao/Repository"},
  {"id": "CONV-M1", "rule": "order 模块不得依赖 promotion 模块"},
  {"id": "CONV-D1", "rule": "领域层(domain)不得依赖基础设施层(infra)"}
]
```

喂入时同时在 report「项目规约」节逐条列出（id + 规约原文），让读者能核对。

## 三、违规检测怎么取证

对每条规约，找**违反它的代码事实**（不是找符合的）：

| 规约类型 | 怎么找违规 | 证据 |
|---------|-----------|------|
| 分层/依赖方向 | 按层（包/目录约定）识别双方，找被禁止方向的 import/引用 | `import`/全限定引用 file:line + 双方所属层 |
| 模块边界 | 找跨禁止边界的类型引用 | 跨模块 import file:line |
| 暴露面 | 找本应封闭却对外可见的实现 | 可见性/包归属 file:line |

- **取引用事实**优先 LSP（`findReferences`/`incomingCalls`），无则 rg 搜全限定名/`#include`（见 `analysis-protocol.md`）。
- **层/模块的识别**用用户喂入的规约里的定义（包名/目录/命名空间），**不**自己发明分层。

## 四、违规 → finding

每条违规产一条 `axis: convention` 的 finding（见 `findings-json-schema.md`）：

- `category`: `convention-violation`
- `convention_violated`: 指向 `convention_rules[].id`（**必填**，这是 convention 轴与 smell 轴的区别）
- `evidence`: 违规的 file:line
- `severity`：按 `severity-and-priority.md` 定级。**违反项目核心分层/边界规则的根因违规** → critical（这是 go/no-go 的 critical 来源之一）；普通违规 → major/minor。
- `impact`/`improvement`/`fix_cost`/`priority` 同其他 finding。

## 五、一致性强约束（`validate_report.py` R-V 硬卡）

- `conventions_fed: true` → report 必须有「项目规约」节 + 至少评估了规约（可以有 0 违规，但要逐条声明「检出/未检出」，不能不提）。
- `conventions_fed: false` → report **不得出现**规约违规结论（`axis: convention` 的 finding 必须为 0）。混入则门不通过。
- findings.json 的 `convention_rules` id 与 report「项目规约」节列出的 id 必须一致（`validate_contract.py` 对账）。

## 六、与通用坏味道的关系

规约违规与通用坏味道可能重叠（如「Controller 直连 Dao」既是通用 cross-layer，也可能违反用户 CONV-L1）。处理：

- **都报**：通用原理违规走 smell 轴（`principle_violated`），规约违规走 convention 轴（`convention_violated`），两条 finding 各自挂证据、各自定级，互不替代——因为它们服务不同读者（通用准则 vs 项目契约）。
- 不要为了「去重」漏报任何一轴。
