# C++ 标准架构做法库

> 配合 `arch-first-code-gen` 的 Checklist 第 2 步。C++ 栈的角色候选池。
>
> **⚠ 能力受限提示**：C++ 无 package 概念，依赖靠 `#include` / 命名空间 / CMake target 依赖；分层与依赖分析**弱于 JVM**（与 `arch-quality-eval` 同口径）。角色划分更靠目录约定与命名空间，架构门对 C++ 的结构性检查更保守、语义项更多登记为缺口。

## 一、分层角色（典型 C++ 后端/服务分层）

| 角色 | 层 | 职责 | 业界做法依据 | 常依据原则 |
|---|---|---|---|---|
| **接入层**（Handler/Controller，brpc/httplib/gRPC service） | controller | 协议接入：收请求、校验、编排、组装响应 | RPC service / 分层架构惯例 | SRP、separation_of_concerns |
| **业务层**（Service/Manager） | service | 用例编排、事务、协调领域对象与仓储 | 应用服务（DDD） | SRP、DIP |
| **持久层**（Repository/Mapper，DAO） | repository | 持久化抽象（MySQL/Redis）；接口与实现可分离 | Repository 模式（PoEAA）/ DAO | DIP |
| **领域层**（Domain） | domain | 领域对象与规则 | DDD | aggregate/entity/… |
| **基础设施 / 公共层**（common/util） | infrastructure/util | 第三方接入、日志、配置、工具 | 分层架构 / 端口适配器 | separation_of_concerns |

> **依赖方向惯例（架构门对 C++ 保守检查）**：接入→业务→持久/领域；`#include` 方向单向、不循环（循环 `#include` 是典型坏味道，可结构性查）；领域层不反向 `#include` 接入层。

## 二、领域角色（DDD 战术映射到 C++）

| 领域角色 | C++ 形态 | 业界做法依据 | 常依据原则 |
|---|---|---|---|
| **聚合根**（Aggregate） | `class OrderAggregate`，封装不变量，对外暴露行为方法 | DDD 聚合 | aggregate、high_cohesion_low_coupling |
| **实体**（Entity） | 有唯一标识的 `class`，行为与数据同体 | DDD 实体 | entity |
| **值对象**（Value Object） | 不可变 `struct/class`，按值判等（如 `Money`） | DDD 值对象 | value_object |
| **领域服务**（Domain Service） | 自由函数或 `class`，跨聚合领域操作 | DDD 领域服务 | domain_service |
| **领域事件**（Domain Event） | 事件 `struct` + 发布订阅（自建/框架） | DDD 领域事件 | domain_event |

## 三、C++ 特别说明

- **头文件与依赖**：依赖关系由 `#include` 表达；**循环 `#include`、下层 include 上层**是结构性坏味道（架构门可查）；用前置声明减少耦合（ISP）。
- **命名空间**：用 `namespace` 表达模块/域边界（如 `com::x::order`），映射限界上下文。
- **目录约定**：`include/<域>/` + `src/<域>/` 分层；新代码沿用既有目录/命名空间约定（模块 A 对齐）。
- **日志库**：spdlog（`spdlog::info/warn/error`）。详见 `logging-standards.md`。
- **所有权/依赖注入**：构造期注入依赖（`std::unique_ptr<IFoo>`/引用），上层不直接 `new` 下层具体（DIP）。

## 四、C++ 角色确认清单（确认时逐条过）

- [ ] 接入/业务/持久/领域 分层是否清晰？`#include` 方向单向、无循环？
- [ ] 命名空间/目录是否表达域边界，且与仓库现有约定一致？
- [ ] 有没有领域角色？C++ 项目常偏「过程式 + 贫血结构」，若引入聚合/值对象要说明收益。
- [ ] 依赖是否构造期注入（DIP），而非上层硬 `new` 下层？
- [ ] 日志用 spdlog、关键节点打点？
- [ ] **诚实登记**：C++ 结构/依赖分析能力受限，语义项（职责是否真单一等）登记为缺口，不假装查了。
