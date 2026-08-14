# Swift/iOS 标准架构做法库

> 配合 `arch-first-code-gen` Checklist 第 2 步。覆盖 SwiftUI 与 UIKit。把角色目录当候选池，先对齐现有工程，再逐项判定适用性；不要为了“用了 MVVM”机械创建空壳层。同时遵循 `../ui-architecture-policy.md`。

## 一、UI 架构模式决策（先确认，不默认脑补）

在角色确认前记录 `SwiftUI | UIKit` 与现有模式：`MVVM | MVC | Coordinator | Clean/VIP | TCA | 其他`。

- **SwiftUI 新页面**：默认把 MVVM 作为首选候选。View 负责声明式渲染与发送用户意图；ViewModel 负责屏幕状态、异步任务生命周期和用例编排。
- **UIKit 现有工程**：优先沿用已有 MVC/MVVM/Coordinator/Clean 等边界，不为模式统一擅自重构。新模块在状态或异步流程明显复杂时，可提出 MVVM 并完成角色确认。
- **纯展示或极简单页面**：允许 View 持有短生命周期、本地且纯 UI 的状态，不强制建立 ViewModel。必须说明“不采用 MVVM”的理由。
- **跨页面共享状态**：不要塞进单个 Screen ViewModel；放到明确的应用状态、Store、用例或领域角色，并声明生命周期与所有权。

结论必须进入角色清单或 `gate.notes`：采用何种模式、为什么、哪些现有约定被沿用。`MVVM` 是职责拆分手段，不是交付目标。

若新引入 MVVM 会重排多个既有页面/模块、导航或共享状态，或改变公共接口与依赖组装，判为高迁移影响；必须在编码前说明范围和替代方案并取得用户明确确认。通用方案确认不能替代这项专项确认。

## 二、分层角色候选

| 角色 | 层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **View**（SwiftUI `View` / UIKit `UIViewController`） | view | 渲染已准备好的 UI 状态，转发用户意图，管理纯展示细节；不直接访问网络/持久化，不承载领域规则 | SwiftUI 声明式 UI / UIKit View-Controller 边界 | SRP、separation_of_concerns |
| **ViewModel**（按需） | view_model | 持有屏幕状态、处理 intent、编排用例、把领域结果映射为 UI 状态；不直接依赖具体 Repository/SDK，不持有 SwiftUI View 或 UIKit 控件 | MVVM Presentation Model | SRP、DIP、separation_of_concerns |
| **Use Case / Application Service**（按需） | application | 表达一个业务用例，协调领域对象与 Repository 抽象；可被多个界面复用 | Clean Architecture Use Case / DDD 应用服务 | SRP、DIP |
| **Repository Protocol** | repository | 定义领域/应用层所需的数据访问能力；接口与实现分离 | Repository 模式 / 端口与适配器 | DIP、ISP |
| **Repository / Client 实现** | infrastructure | 使用 URLSession、SwiftData/Core Data、Keychain 或第三方 SDK 实现端口，完成 DTO 映射 | Adapter / Repository 实现 | DIP、separation_of_concerns |
| **Coordinator / Router**（按需） | coordinator | 集中导航决策与页面组装；View/ViewModel 只发出导航意图 | Coordinator 模式 | SRP、high_cohesion_low_coupling |
| **Composition Root / Factory** | composition | 在 App/Scene/feature 入口组装具体依赖和生命周期；业务角色不自行创建基础设施实现 | Composition Root / Dependency Injection | DIP、dependency_direction |
| **Mapper / DTO**（按需） | mapper | 在网络/持久化模型、领域模型、UI Model 之间转换；不混入业务规则 | Data Mapper / DTO | separation_of_concerns |

> **默认依赖方向**：`View → ViewModel → UseCase/Application → Repository Protocol / Domain`，`Infrastructure → Repository Protocol`；Composition Root 创建具体实现并注入。Coordinator 负责导航，不能反向吸收业务规则。

若不采用 ViewModel，必须把替代依赖方向写清楚，例如简单 SwiftUI View 直接依赖只读 presentation model，但仍不得直接 new 网络/数据库实现。

## 三、领域角色候选（DDD 战术）

| 领域角色 | Swift 形态 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **聚合根** | `struct`/`final class`，通过行为维护不变量 | 作为一致性边界和对外唯一修改入口 | DDD 聚合 | aggregate、high_cohesion_low_coupling |
| **实体** | 带稳定 identity 的类型 | 承载生命周期与领域行为 | DDD 实体 | entity、tell_dont_ask |
| **值对象** | 不可变 `struct`，按值判等 | 表达金额、标识、区间等领域概念并在构造时校验 | DDD 值对象 | value_object |
| **领域服务** | 无状态类型/协议实现 | 承载不自然属于单一实体的领域操作 | DDD 领域服务 | domain_service、SRP |
| **领域事件** | 不可变事件 `struct` | 表达已发生事实，解耦后续反应 | DDD 领域事件 | domain_event、separation_of_concerns |

UI-only feature 没有复杂业务规则时，可以不创建领域角色，但要明确“本 feature 仅改变呈现/交互，不新增领域不变量”。不要把 ViewModel 伪装成领域层。

## 四、SwiftUI 状态与并发

- 使用 Observation（`@Observable`）或工程既有的 `ObservableObject` 方案；同一状态只保留一个事实源，避免 View、ViewModel、Store 重复持有可变副本。
- 会更新 UI 状态的 ViewModel 通常隔离到 `@MainActor`；耗时工作放到异步依赖，不在主 actor 执行阻塞 I/O。
- 优先 `async/await` 与结构化并发；声明任务所有者、取消时机和重复触发策略。不要在 View body 中启动不可控副作用。
- 跨并发边界的数据按项目 Swift 版本处理 `Sendable`；不要用无约束 `Task.detached` 绕过隔离。
- ViewModel 把错误映射为明确 UI state；领域/基础设施错误类型不直接泄漏成展示文案。

## 五、UIKit 特别说明

- `UIViewController` 负责视图生命周期、绑定和事件转发，不直接承担网络、持久化和领域规则。
- 使用 MVVM 时，绑定方向和生命周期必须明确；避免 ViewModel 持有 ViewController 形成环。
- 使用 Coordinator 时，导航依赖通过协议/闭包/路由事件表达，按现有工程约定取舍。
- 若仓库是成熟 MVC，不要仅因本库存在 ViewModel 就重写；先判断当前 feature 能否在既有职责边界内实现。

## 六、测试与可观察性

- ViewModel/UseCase 使用协议注入，测试状态转换、成功/失败/取消和重复触发。
- Repository 实现测试映射与错误转换；领域对象测试不变量。
- SwiftUI Preview/截图测试使用稳定 fixture，不接真实网络。
- 使用 `OSLog.Logger` 记录用例入口/结果、外部调用和异常；不要在 `body` 重算或每次渲染时打日志。隐私数据使用 privacy 标注或不记录。

## 七、MVVM 反模式

| 反模式 | 正确做法 |
|---|---|
| View 直接调用 URLSession/数据库 | 通过 ViewModel/UseCase 和 Repository 抽象 |
| Massive ViewModel 包含导航、格式化、领域规则、存储 | 按变化原因拆 UseCase、Coordinator、Mapper、Domain |
| 为纯展示页创建空 ViewModel | 保留简单 View，本地 UI 状态就近管理并说明理由 |
| ViewModel 持有 View/UIViewController | 输出状态和事件，不反向持有 UI |
| View 与 ViewModel 各维护一份业务状态 | 单一事实源，派生状态计算得到 |
| 为引入 MVVM 重写成熟 UIKit 模块 | 沿用现有模式；仅在新需求需要时调整并确认 |

## 八、角色确认清单

- [ ] 已识别 SwiftUI/UIKit 与仓库现有 UI 模式？
- [ ] 已明确采用或不采用 MVVM，并写出具体理由？
- [ ] View 是否只渲染/转发 intent，没有直接网络、持久化或领域规则？
- [ ] ViewModel 是否只负责 presentation state 和用例编排，没有变成万能层？
- [ ] 依赖是否由 Composition Root 注入，方向是否指向抽象？
- [ ] UI 状态是否有单一事实源，`@MainActor`、任务取消和错误映射是否明确？
- [ ] 领域角色适用性是否检查过；不适用是否说明？
- [ ] 日志是否使用 OSLog、保护隐私且避开高频渲染路径？
- [ ] 新代码是否沿用现有目录、命名、依赖注入和测试习惯？
- [ ] 若新引入 MVVM 的迁移影响为 high，是否已有用户明确确认？
