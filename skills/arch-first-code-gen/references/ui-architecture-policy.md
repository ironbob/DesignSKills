# 跨语言 UI 架构与 MVVM 决策策略

> 适用于本 skill 支持的所有语言中的 UI 代码，包括 Android、Vue、Qt/QML、SwiftUI/UIKit。后端、命令行和纯基础设施代码不套用 MVVM。

## 一、先识别现状，再选择目标模式

编码前先从相关目录、相邻页面和依赖组装处识别并记录：

1. UI 框架与页面边界；
2. 当前模式（MVVM、MVC、MVP、Store/Redux、TCA、Clean/VIP、Direct View 或其他）；
3. 状态事实源、导航所有者、异步任务与依赖注入方式；
4. 本 feature 若采用 MVVM，会影响哪些文件、模块、公共接口、导航和测试。

不得仅凭语言或 UI 框架断言“必须 MVVM”，也不得忽略已有且职责清晰的架构。

## 二、MVVM 是适用时的优先方案，不是机械模板

以下情况通常适合优先采用或继续采用 MVVM：

- 页面存在异步加载、重试、提交、分页或多状态转换；
- 展示状态需要由多个领域/数据来源组合得到；
- 用户意图与 UI 状态转换值得独立单测；
- 工程已经以 ViewModel、presentation model、feature store 或同等边界组织 UI；
- View 正在直接承担请求、持久化、领域规则或复杂编排，需要拆开变化原因。

以下情况可以不采用 MVVM：

- 纯展示或仅有短生命周期、局部、纯视觉状态；
- 工程已有职责清楚且一致的 TCA、Redux/Store、MVP、MVC、Clean/VIP 等模式；
- 新建 ViewModel 只会转发字段和方法，形成空壳层；
- 迁移成本明显高于本 feature 的可测试性、状态管理或职责分离收益。

“适合则尽量使用”意味着：适用且迁移影响为 `none/low/medium` 时，把 MVVM 作为首选；若仍选择其他模式，必须写出与现状和 feature 复杂度相关的具体理由。不要为满足名称创建空 ViewModel。

## 三、较大迁移必须由用户明确确认

出现以下一项或多项时，通常将 `migration_impact` 判为 `high`：

- 需要重排多个既有层、模块或大量页面/组件的职责；
- 需要迁移全局/跨页面状态、导航所有权或生命周期；
- 需要更改公共 API、依赖注入/组装方式或跨模块依赖方向；
- 需要让多个既有调用方、共享组件或广泛测试随之修改；
- 本 feature 无法以局部兼容层或渐进方式引入 MVVM。

若目标方案是**新引入 MVVM**且 `migration_impact=high`：

1. 编码前向用户说明现状、迁移范围、收益、风险和较小改动的替代方案；
2. 将 `migration_confirmation` 记为 `pending` 并暂停；
3. 只有用户明确同意后改为 `user_confirmed`，才能进入编码。

主 skill 的通用方案确认不能代替这项专项确认。用户说“无需中间确认”不能绕过双确认门禁，也不能授权大范围 UI 架构迁移。

## 四、跨框架的角色映射

| 概念角色 | 常见实现 |
|---|---|
| View | SwiftUI View / UIViewController、Compose/Activity/Fragment、Vue Page/Component、QML/Qt Widget |
| ViewModel | Swift observable state holder、AndroidX ViewModel、Vue feature store/composable/presentation model、Qt `QObject` presentation object |
| Model / Use Case | 领域对象、应用服务、use case |
| Repository / Port | 数据访问抽象；具体网络、数据库或 SDK 实现在基础设施层 |

Vue/Store 或 Qt 项目不要求为了叫“MVVM”创建特定后缀的类；已有对象只要真实承担屏幕状态、用户意图处理与用例编排，就可作为 ViewModel 角色记录。全局 Store 不自动等于 ViewModel，必须说明作用域和职责。

## 五、契约留痕

所有 UI feature 在 `ui_architecture` 中记录：

- `framework`、`current_patterns`、`target_patterns`；
- `state_management`、`view_model_policy`、`mvvm_suitability`；
- `migration_impact`、`impact_scope`、`migration_confirmation`；
- `decision_reason`。

采用 MVVM 时必须存在 `layer=view_model` 角色；不采用时不得创建名义 ViewModel。高影响的新 MVVM 迁移没有 `user_confirmed` 证据时，契约校验必须失败。
