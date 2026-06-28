# JVM(Java/Kotlin) 标准架构做法库

> 配合 `arch-first-code-gen` 的 Checklist 第 2 步。JVM 栈（Java/Kotlin，典型 Spring Boot / Ktor）的角色候选池。**对照具体需求逐条判适用性，不照搬。**

## 一、分层角色（技术分层）

| 角色 | 层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **Controller**（`@RestController`/`@Controller`） | controller | 协议适配：收 HTTP 请求、校验入参（`@Valid`）、编排调用、组装响应；**不含业务逻辑** | MVC Controller / Spring Web 惯例 | SRP、separation_of_concerns |
| **Service**（`@Service`，应用服务） | service | 用例编排：事务边界、协调领域对象与仓库、跨聚合流程；**不含协议细节** | 应用服务（DDD）/ Spring `@Service` 惯例 | SRP、DIP、separation_of_concerns |
| **Repository**（接口 + 实现，`@Repository`/JPA/MyBatis） | repository | 持久化抽象：聚合的存取；**接口属领域层，实现属基础设施层** | Repository 模式（PoEAA）/ DDD | DIP、dependency_direction |
| **Facade / 协调器**（按需） | service/facade | 复杂跨子系统的协调入口（子系统多时） | Facade 模式（PoEAA） | SRP、separation_of_concerns |
| **Infrastructure 适配器** | infrastructure | 外部系统接入（MQ/缓存/第三方 API）、Repository 实现、技术横切 | 六边形架构（端口与适配器） | DIP、separation_of_concerns |

> **依赖方向惯例（架构门可结构性查）**：`controller → service → repository 接口 / 领域对象`；领域层不反向依赖 controller/service；Repository 接口属领域层、实现属基础设施层（DIP）。

## 二、领域角色（DDD 战术，业务建模）

| 领域角色 | 住哪层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **聚合根**（Aggregate） | domain | 一致性边界、对外唯一入口、封装不变量 | DDD 聚合 | aggregate、high_cohesion_low_coupling |
| **实体**（Entity） | domain | 有唯一标识、生命周期、行为 | DDD 实体 | entity |
| **值对象**（Value Object） | domain | 无身份、不可变、按值判等（如 `Money`/`Address`） | DDD 值对象 | value_object |
| **领域服务**（Domain Service） | domain | 不属任一实体的领域操作（跨聚合） | DDD 领域服务 | domain_service |
| **领域事件**（Domain Event，`@DomainEvent`/Spring Events） | domain | 领域发生的事实，解耦通知（如 `OrderCreatedEvent`） | DDD 领域事件 / 事件驱动 | domain_event、separation_of_concerns |

## 三、JVM 特别说明

- **贫血 vs 充血**：避免贫血模型（只有 getter/setter 的实体）。领域行为归聚合/实体（Tell-Don't-Ask）。
- **包结构惯例**：`com.x.<域>.controller/service/repository/domain`；新代码沿用既有包约定（模块 A 对齐）。
- **日志库**：SLF4J 接口 + Logback 实现（`private static final Logger log = LoggerFactory.getLogger(...)`）。详见 `logging-standards.md`。
- **事务**：`@Transactional` 放应用服务层（用例边界），不放 controller。

## 四、JVM 角色确认清单（确认时逐条过）

- [ ] 用了哪几个分层角色？每个职责单一（SRP）？
- [ ] 依赖方向：controller→service→repository/领域，无反向、无跨层？
- [ ] 有没有领域角色（聚合/实体/值对象…）？纯 CRUD 可只有分层角色，但要说明「无复杂领域逻辑故不用聚合根」。
- [ ] Repository 是接口+实现分离（DIP）还是简单直接用框架？按需求复杂度取舍。
- [ ] 新代码的包/命名/日志库与仓库现有一致（模块 A 对齐）？
