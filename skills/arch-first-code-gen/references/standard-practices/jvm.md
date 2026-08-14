# JVM(Java/Kotlin) 标准架构做法库

> 配合 `arch-first-code-gen` 的 Checklist 第 2 步。JVM 栈（Java/Kotlin，包含 Spring Boot / Ktor 与 Android）的角色候选池。**对照具体需求逐条判适用性，不照搬。** Android UI 同时遵循 `../ui-architecture-policy.md`。

## 一、分层角色（技术分层）

| 角色 | 层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **Controller**（`@RestController`/`@Controller`） | controller | 协议适配：收 HTTP 请求、校验入参（`@Valid`）、编排调用、组装响应；**不含业务逻辑** | MVC Controller / Spring Web 惯例 | SRP、separation_of_concerns |
| **Service**（`@Service`，应用服务） | service | 用例编排：事务边界、协调领域对象与仓库、跨聚合流程；**不含协议细节** | 应用服务（DDD）/ Spring `@Service` 惯例 | SRP、DIP、separation_of_concerns |
| **Repository**（接口 + 实现，`@Repository`/JPA/MyBatis） | repository | 持久化抽象：聚合的存取；**接口属领域层，实现属基础设施层** | Repository 模式（PoEAA）/ DDD | DIP、dependency_direction |
| **Facade / 协调器**（按需） | service/facade | 复杂跨子系统的协调入口（子系统多时） | Facade 模式（PoEAA） | SRP、separation_of_concerns |
| **Infrastructure 适配器** | infrastructure | 外部系统接入（MQ/缓存/第三方 API）、Repository 实现、技术横切 | 六边形架构（端口与适配器） | DIP、separation_of_concerns |

> **依赖方向惯例（架构门可结构性查）**：`controller → service → repository 接口 / 领域对象`；领域层不反向依赖 controller/service；Repository 接口属领域层、实现属基础设施层（DIP）。

## 二、Android UI 角色与 MVVM 决策

先检查工程是 Compose、Views 还是混合，以及相邻 screen 当前使用 AndroidX ViewModel、plain state holder、MVI/Redux 或其他模式。不要把所有 Kotlin/Java 代码都当 UI，也不要为可复用小组件机械创建 ViewModel。

- **适合 MVVM**：screen 有异步数据、业务状态、跨配置变化状态或可独立测试的意图/状态转换时，优先 `Screen View → AndroidX ViewModel → UseCase/Repository`。
- **简单 UI**：纯展示和局部纯 UI 状态可用 Compose state hoisting 或 plain state holder，不要求 ViewModel。
- **已有替代架构**：工程已有清晰的 MVI/Redux/Clean 边界时先沿用；若 MVVM 更合适但迁移影响高，必须先取得用户明确确认。
- **作用域**：ViewModel 通常放在 screen/destination 级；可复用 UI 组件优先使用普通 state holder，不滥用 screen ViewModel。

| 角色 | 层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **Compose Screen / Activity / Fragment** | view | 渲染 UI state、转发用户意图、管理纯展示生命周期；不直接访问数据源 | Android UI layer / UDF | SRP、separation_of_concerns |
| **AndroidX ViewModel**（按需） | view_model | 提供 screen UI state、处理意图、编排 UI 层业务逻辑；不持有 Activity/View/Context | Android architecture ViewModel | SRP、DIP、separation_of_concerns |
| **Use Case**（按需） | application | 复用或简化跨 ViewModel 的业务逻辑 | Android domain layer / Clean Architecture | SRP、DIP |
| **Repository** | repository | 向 UI/domain 暴露应用数据，不让 View/ViewModel 直接接触数据源 | Repository pattern / Android architecture | DIP、dependency_direction |

状态优先采用工程既有方案；新 Compose 代码常以不可变 `UiState` + `StateFlow` 暴露状态，并进行 lifecycle-aware collection。具体版本/API 以项目依赖为准。

## 三、领域角色（DDD 战术，业务建模）

| 领域角色 | 住哪层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **聚合根**（Aggregate） | domain | 一致性边界、对外唯一入口、封装不变量 | DDD 聚合 | aggregate、high_cohesion_low_coupling |
| **实体**（Entity） | domain | 有唯一标识、生命周期、行为 | DDD 实体 | entity |
| **值对象**（Value Object） | domain | 无身份、不可变、按值判等（如 `Money`/`Address`） | DDD 值对象 | value_object |
| **领域服务**（Domain Service） | domain | 不属任一实体的领域操作（跨聚合） | DDD 领域服务 | domain_service |
| **领域事件**（Domain Event，`@DomainEvent`/Spring Events） | domain | 领域发生的事实，解耦通知（如 `OrderCreatedEvent`） | DDD 领域事件 / 事件驱动 | domain_event、separation_of_concerns |

## 四、JVM 特别说明

- **贫血 vs 充血**：避免贫血模型（只有 getter/setter 的实体）。领域行为归聚合/实体（Tell-Don't-Ask）。
- **包结构惯例**：`com.x.<域>.controller/service/repository/domain`；新代码沿用既有包约定（模块 A 对齐）。
- **日志库**：SLF4J 接口 + Logback 实现（`private static final Logger log = LoggerFactory.getLogger(...)`）。详见 `logging-standards.md`。
- **事务**：`@Transactional` 放应用服务层（用例边界），不放 controller。
- **无构建工具的最小验证**：空仓库或轻量库没有 Maven/Gradle 时，可先用 `javac -d <temp>` 编译 source/test fixture，并运行带断言的测试入口；不要为一个 feature 静默引入构建系统。

## 五、JVM 角色确认清单（确认时逐条过）

- [ ] 用了哪几个分层角色？每个职责单一（SRP）？
- [ ] 依赖方向：controller→service→repository/领域，无反向、无跨层？
- [ ] 有没有领域角色（聚合/实体/值对象…）？纯 CRUD 可只有分层角色，但要说明「无复杂领域逻辑故不用聚合根」。
- [ ] Repository 是接口+实现分离（DIP）还是简单直接用框架？按需求复杂度取舍。
- [ ] 新代码的包/命名/日志库与仓库现有一致（模块 A 对齐）？
- [ ] 若是 Android UI，是否先识别现有模式并判断 MVVM 适用性，而不是机械创建 ViewModel？
- [ ] 若新引入 MVVM 的迁移影响为 high，是否已有用户明确确认？
