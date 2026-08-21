# 设计契约 checklist（模块 C 前置 — 软引导）

> 把模块 B 确认的角色/职责/依赖固化为编码对照。以《代码大全2》的复杂度管理、信息隐藏和构造质量为主；SOLID/DDD/分层只作为解释具体边界的次级工具。

## 一、为什么固化成 checklist

模块 B 确认了「应该是什么样」，编码时容易跑偏（顺手把多个职责塞进一个类、依赖方向写反）。checklist 把确认结果变成编码时**随手可查的对照表**，让「设计思想」在编码时持续在场——回答 PRD 的追问「编码时怎么确保真正遵守了好的实践」。

## 二、checklist 条目结构（契约源 `design_contract_checks[]`）

| 字段 | 说明 |
|---|---|
| `id` | `DC-<n>` |
| `item` | 对照条目（编码时检查的陈述），如「依赖方向 controller→service→repository，不反向」 |
| `principle` | 对应原则；优先使用 `code-complete-design.md` 的 `cc_*` ID |
| `role_scope` | 该条约束的角色 id（可空 = 全局） |

## 三、典型条目（按需求取舍，不照搬）

**复杂度 / 信息隐藏 / 职责**
- 角色隐藏一个明确易变决策，调用方不依赖其内部表示（`cc_information_hiding`）。
- 只保留当前验收和风险需要的角色/接口/扩展点（`cc_manage_complexity` / `cc_lean_design`）。
- 角色高内聚、协作低耦合，接口最小并维持有效状态（`cc_strong_cohesion` / `cc_loose_coupling` / `cc_class_contract`）。
- 每个角色只承担一类职责，不混入不相关逻辑（SRP）。
- 协议适配 / 业务编排 / 持久化 / 横切（日志/鉴权）分开，不混在一个角色（separation_of_concerns）。
- 领域行为归聚合/实体，不贫血（Tell-Don't-Ask）。
- 每个角色明确隐藏的变化秘密、变化触发器和数据所有权（information_hiding）。

**依赖方向**
- 依赖单向、指向稳定方；上层不直接 new/依赖下层具体，靠抽象（DIP/dependency_direction）。
- 领域层不反向依赖 controller/service。
- Repository 接口与实现分离（DIP）。

**接口/扩展**
- 接口按调用方需要拆，不被迫依赖用不到的方法（ISP）。
- 加新策略不改老代码（OCP）——有扩展点时才立这条，YAGNI。
- 跨角色接口在编码前明确输入/输出、前置/后置条件、不变量、错误与事务/并发边界（defensive_design）。

**构造 / 验证 / 风险**
- 复杂例程先按 PPP 梳理步骤；例程单一目的、控制流直接、变量小作用域且单用途。
- 外部输入防御、内部断言和错误边界分开；不稳定依赖可替换并能观察结果。
- 小步重构，每个语义批次后编译并运行最相关测试。
- 关键质量属性、不变量和异常路径都有验证方式与可追溯证据（minimize_complexity）。
- 高风险技术假设已有最小 spike 结论；未验证项明确影响和后续动作。

**复用领域角色**
- 值对象用类型而非基本类型（如 `Money` 而非 `int`）（value_object）。
- 聚合根封装一致性不变量，外部不跨聚合直接改内部（aggregate）。

**UI / MVVM（仅 UI feature）**
- View 负责渲染与转发 intent；采用 MVVM 时，ViewModel 负责 presentation state 与用例编排，不直接持有 View 或具体基础设施（SRP/DIP）。
- 纯展示和局部纯 UI 状态不机械创建 ViewModel；采用替代模式时仍保持单一事实源与明确依赖方向（separation_of_concerns）。
- 高影响的新 MVVM 迁移必须已有用户明确确认；确认前不进入编码（dependency_direction）。

## 四、怎么用（编码时）

1. 编码每个角色前，扫一眼约束它的 checklist 条目（按 `role_scope` 过滤）。
2. 编码中对照提醒——发现要违反某条时，停下来：要么改设计（回模块 B 确认），要么确认这条不适用并说明。
3. **不逐角色硬卡**：checklist 是提醒不是阻断；真正需要停下来的，是发现职责边界、依赖方向、领域建模等原则被破坏。

## 五、反模式

| 反模式 | 正确做法 |
|---|---|
| 把 checklist 当逐角色硬门禁（编码中频繁打断） | 软引导；以最终原则复核 + 必要结构证据为准 |
| checklist 条目空泛（「要写好代码」） | 具体可对照：「依赖方向 controller→service，不反向」 |
| 编码跑偏了不回看 checklist | 对照提醒；违反时停下来改设计或说明不适用 |
| 为了凑条目硬塞扩展点（YAGNI 违反） | 有真实扩展需求才立 OCP 类条目 |
