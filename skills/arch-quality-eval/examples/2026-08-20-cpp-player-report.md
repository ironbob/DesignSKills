---
schema_version: 2
module: cpp-player
title: cpp-player 架构设计质量诊断
language: C++
analyzed_at: 2026-08-20
scope_files:
  - include/domain/PlaybackService.hpp
  - include/infra/MediaStore.hpp
  - include/ui/PlayerController.hpp
  - src/PlayerController.cpp
indexed_file_count: 4
inspected_file_count: 4
semantic_resolved_file_count: 4
coverage_sufficient: true
conventions_fed: false
no_go_threshold: 1
verdict: go
critical_count: 0
major_count: 1
minor_count: 0
confirmed_critical_count: 0
cpp_limitation_noted: true
open_questions: 0
status: draft
---

# cpp-player 架构设计质量诊断

> 以复杂度管理、职责边界、依赖、信息隐藏、抽象一致性和变化隔离为主轴；不检查语法、语言技巧、lint 或 CI。

## 一、范围与覆盖

- **路径**：`include`、`src`。
- **职责基线**：接收播放请求、检查媒体存在性并调用播放服务。
- **结构**：media::ui、media::domain、media::infra 三个职责区域。
- **覆盖**：范围 4，索引 4，精读 4，语义解析 4 个文件。
- **结论覆盖充分性**：充分。

## 二、诊断结论

**✅ go** —— confirmed critical 0，阈值 1。

在声明覆盖内未发现 confirmed critical，可按优先级增量治理。

## 三、设计原则矩阵

| 设计轴 | 状态 | 结论 | 代表证据 |
|---|---|---|---|
| 复杂度管理 (`complexity-management`) | ✅ no material concern | 模块规模小，没有额外控制中心或无收益间接层。 | include/ui/PlayerController.hpp:8 |
| 职责与内聚 (`responsibility-cohesion`) | ✅ no material concern | 三个类型名称和主要职责可区分。 | include/domain/PlaybackService.hpp:5 |
| 耦合与依赖方向 (`coupling-dependency-direction`) | ⚠ concern | UI 控制器直接持有基础设施存储依赖。 | include/ui/PlayerController.hpp:10 |
| 信息隐藏与接口边界 (`information-hiding`) | ✅ no material concern | 未发现额外公共接口泄漏内部数据布局。 | include/infra/MediaStore.hpp:5 |
| 抽象层级一致性 (`abstraction-consistency`) | ⚠ concern | UI 请求适配同时掌握播放策略和存储检查机制。 | include/ui/PlayerController.hpp:14 |
| 变化隔离与可演进性 (`change-isolation`) | ✅ no material concern | 当前静态结构没有显示同一变化散落在多个无关实现中。 | src/PlayerController.cpp:1 |

## 四、结构问题

#### FINDING-D01 · PlayerController 直接依赖 MediaStore · 🟠 major · confidence=confirmed

- 证据：`include/ui/PlayerController.hpp:10`（PlayerController accepts infra MediaStore dependency）；`include/ui/PlayerController.hpp:14`（exists）
- 违反原则：coupling-dependency-direction、abstraction-consistency
- 关联规约：—
- 影响：存储变化会传播到 UI，请求适配器还掌握基础设施检查步骤。
- 分级依据：影响核心播放路径，但可通过稳定服务边界增量治理，因此为 major。
- 改进方向：把媒体存在性检查封装到应用或领域服务边界。
- 修复成本：medium　优先级：P1（这是唯一确认的结构问题，影响主路径且治理成本可控。）

## 五、架构可理解性

**mixed** —— 角色名称清楚，但 UI 依赖 infra 使请求边界与存储机制混杂。

## 六、优先级

| 优先级 | finding | 排序依据 |
|---|---|---|
| P1 | FINDING-D01 | 这是唯一确认的结构问题，影响主路径且治理成本可控。 |

## 七、方法与缺口

- **取证方式**：compile_commands + clang AST；语言工具只提供架构证据。
- **聚焦策略**：用 AST 定位 PlayerController 的类型依赖，再阅读接口确认三者架构角色。
- **Git 历史**：不可用或未采样。
- **未覆盖**：不检查 C++ 语法质量、模板技巧或所有权风格。
- **覆盖缺口**：AST 只覆盖 compile database 中成功解析的翻译单元；宏和未激活条件分支未覆盖。
- **边界**：仅做重构前架构诊断；完整重构方案、语法检查和语言技巧不在范围内。
