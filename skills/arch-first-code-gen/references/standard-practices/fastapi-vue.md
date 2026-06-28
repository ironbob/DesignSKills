# FastAPI + Vue 标准架构做法库

> 配合 `arch-first-code-gen` 的 Checklist 第 2 步。FastAPI(后端) + Vue(前端) 全栈的角色候选池。**对照具体需求逐条判适用性。**

## 一、后端角色（FastAPI / Python）

### 分层角色

| 角色 | 层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **Router**（`APIRouter`） | router | 路由 + 协议适配：收请求、Pydantic 校验、调 service、组装响应；**不含业务** | FastAPI 惯例 / MVC Controller | SRP、separation_of_concerns |
| **Service**（应用服务） | service | 用例编排、事务、协调领域对象与仓储 | 应用服务（DDD） | SRP、DIP |
| **Repository**（仓储） | repository | 持久化抽象（SQLAlchemy），接口与实现分离（依赖倒置） | Repository 模式（PoEAA）/ DDD | DIP、dependency_direction |
| **Schema**（Pydantic Model） | router/util | 请求/响应 DTO（边界模型，区别于领域模型） | DTO 模式 / FastAPI 惯例 | separation_of_concerns |
| **Infrastructure** | infrastructure | DB session、第三方 SDK、消息队列接入 | 端口与适配器 | DIP、separation_of_concerns |

### 领域角色（DDD 战术）

| 领域角色 | Python 形态 | 业界做法依据 | 常依据原则 |
|---|---|---|---|
| **聚合根** | `@dataclass`/类，封装不变量与行为 | DDD 聚合 | aggregate、high_cohesion_low_coupling |
| **实体** | 有唯一标识的类 | DDD 实体 | entity |
| **值对象** | 不可变 `@dataclass(frozen=True)`（如 `Money`） | DDD 值对象 | value_object |
| **领域服务** | 模块级函数/类，跨聚合操作 | DDD 领域服务 | domain_service |
| **领域事件** | 事件 `@dataclass` + 发布（自建/bus） | DDD 领域事件 | domain_event |

> **依赖方向**：`router → service → repository 接口 / 领域`；领域不反向依赖 router；Repository 接口属领域/抽象层、SQLAlchemy 实现属基础设施（DIP）。

## 二、前端角色（Vue 3 / Composition API）

| 角色 | 层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **View/Page 组件** | view | 页面编排：组合子组件、接 store/接口、页面级布局 | Vue 页面组件惯例 | SRP、separation_of_concerns |
| **业务组件** | view | 可复用业务 UI 单元，props in / events out（单向数据流） | 组件化 / smart-dumb 组件 | SRP、ISP（props 精简） |
| **Store**（Pinia） | store | 跨组件共享状态 + 与状态相关的动作；**不掺 UI** | Pinia 状态管理惯例 | SRP、separation_of_concerns |
| **API Client**（composable / service） | infrastructure | 封装后端调用（axios/fetch）、请求/响应映射 | Service 层 / API 封装惯例 | separation_of_concerns、DIP |
| **Composable**（`useXxx`） | util/infrastructure | 可复用逻辑（副作用、工具），与组件解耦 | Vue Composition API 惯例 | high_cohesion_low_coupling |

> **前端依赖方向**：`View → Store → API Client`；组件靠 props/events 通信（Tell-Don't-Ask 的前端版：把行为/数据交给 store/composable，组件只负责呈现 + 发事件）。

## 三、FastAPI + Vue 特别说明

- **后端日志**：Python `logging` 或 `loguru`，结构化（JSON）；详见 `logging-standards.md`。
- **前端日志**：关键交互/异常打点（埋点/错误上报），不在前端做 debug 级噪音。
- **DTO ≠ 领域模型**：Pydantic Schema 是边界模型，领域用领域对象，不混用（separation_of_concerns）。
- **目录约定**：后端 `app/routers/services/repositories/domain`；前端 `src/views/components/stores/api/composables`；新代码沿用既有约定（模块 A 对齐）。

## 四、全栈角色确认清单（确认时逐条过）

- [ ] 后端 router/service/repository 分层清晰、依赖方向单向？DTO 与领域模型分离？
- [ ] 前端 View/Store/API Client/组件 职责清晰、props-events 单向数据流？
- [ ] 有没有领域角色（后端）？纯 CRUD 接口可只有分层角色，但说明理由。
- [ ] 前端是否避免「组件里直接发请求 + 管状态」混在一起（抽 store/api client）？
- [ ] 新代码目录/命名/日志库与仓库现有一致（模块 A 对齐）？
