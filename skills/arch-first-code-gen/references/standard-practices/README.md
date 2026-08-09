# 按栈标准做法库（索引）

> 配合 `arch-first-code-gen` 的 Checklist 第 2 步。按确认的技术栈加载对应文件。每套含**分层角色 + 领域角色(DDD)**，定义源自业界通行做法，标注依据原则。
>
> **这是确认角色的参考底座，不是要照搬的模板**：对照具体需求逐条判「适用 / 调整 / 不适用」，只采用过判断的结论。禁止整段照抄。

凡涉及 UI，还必须先加载同级 `../ui-architecture-policy.md`：先识别现有模式，适用时优先 MVVM；若新引入 MVVM 会造成较大架构迁移，取得用户明确确认前不得编码。

## 索引

| 栈 | 文件 | 覆盖 |
|---|---|---|
| **JVM**（Java/Kotlin） | `jvm.md` | 服务端分层与领域角色；Android Compose/Views 的自适应 MVVM 做法 |
| **C++** | `cpp.md` | 服务端分层与领域角色；Qt/QML/Widgets 的自适应 MVVM 做法（标注能力受限） |
| **FastAPI + Vue** | `fastapi-vue.md` | 后端分层与领域角色；Vue View / feature Store/Composable 的 MVVM 角色映射 |
| **Swift/iOS** | `swift-ios.md` | SwiftUI/UIKit 模式决策；View / ViewModel / UseCase / Repository / Coordinator / Composition Root + 领域角色 |

## 怎么用

1. 确认栈（模块 A）后加载对应文件。
2. 把它的角色目录当作「候选池」，结合需求逐条判：这个角色**这个需求用不用？职责怎么定？依赖谁？** 不适用就划掉并说明。
3. 每采用的角色填契约源 `industry_basis`（指向业界做法）+ `design_principles`（指向 `design-principles.md` 的原则）。

## 怎么扩展（新栈 / 新角色）

- 新栈：在本目录加 `<stack>.md`，保持「分层角色 + 领域角色 + 依赖方向惯例 + 业界来源标注」结构，更新本索引表。
- 新角色：加到对应栈文件的目录，标 `industry_basis` + `design_principles`；领域角色优先对齐 DDD 战术模式，不自造术语。

> 所有角色定义**必须能回链业界来源**（分层架构 / DDD / PoEAA 模式 / 框架惯例），不凭空设计（PRD §6 角色库来源）。
