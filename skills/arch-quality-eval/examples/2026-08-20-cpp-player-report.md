---
module: cpp-player
title: C++ 播放控制模块架构质量诊断
language: C++
analyzed_at: 2026-08-20
covered_files:
  - include/domain/PlaybackService.hpp
  - include/infra/MediaStore.hpp
  - include/ui/PlayerController.hpp
  - src/PlayerController.cpp
conventions_fed: false
no_go_threshold: 1
verdict: go
critical_count: 0
major_count: 1
minor_count: 0
cpp_limitation_noted: true
open_questions: 0
status: draft
---

# cpp-player 架构质量诊断报告

> 重构前诊断：只回答模块是否值得重构、阻塞点和优先顺序；不输出完整重构方案，不做 lint 或 CI 卡关。

## 一、评估范围

- **路径**：`include`、`src`。
- **覆盖文件**：4 个源文件，详见 frontmatter。
- **语言与结构**：C++；C++ namespace media::ui/domain/infra；compile_commands 覆盖 PlayerController.cpp。
- **模块职责基线**：负责接收播放请求、检查媒体存在性并调用播放服务。
- **项目规约**：未喂入，只检查通用架构准则。

## 二、go/no-go 门禁结论

**✅ go** —— critical 0，阈值 1。

未发现达到 critical 的阻塞问题，可以按优先级增量治理。

## 三、架构坏味道清单

| 核心坏味道 | 判定 | 证据锚点 |
|---|---|---|
| 循环依赖 circular-dependency | ⬜ 未检出 | — |
| God Class / God Package | ⬜ 未检出 | — |
| 跨层调用 cross-layer | ✅ 已检出 → FINDING-S01 | include/ui/PlayerController.hpp:10 |
| 霰弹式修改 shotgun-surgery | ⬜ 未检出 | — |
| 不恰当暴露 inappropriate-exposure | ⬜ 未检出 | — |

#### FINDING-S01 · PlayerController 直接依赖 MediaStore，UI 穿透到基础设施层 · 🟠 major

- 证据：`include/ui/PlayerController.hpp:10`（PlayerController constructor accepts infra::MediaStore and stores the dependency）；`include/ui/PlayerController.hpp:14`（store_.exists calls MediaStore directly from the UI controller）
- 违反原理：分层不穿透、依赖倒置原则
- 影响：UI 请求处理与存储实现耦合，存储接口变化会直接影响控制器，且播放策略可能绕过领域服务。
- 分级依据：clang AST 实锤 UI 类型到 infra 类型的字段和成员调用边；影响核心播放路径，但可通过服务边界增量治理，因此为 major。
- 改进方向：把媒体存在性检查收口到领域/应用服务接口，使 UI 只依赖上层抽象。
- 修复成本：medium　优先级：P1（这是唯一检出的结构问题，影响主播放路径且治理成本可控，应优先处理。）

## 四、架构可读性

| 轴 | 结论 |
|---|---|
| 职责清晰度 | 一般：PlayerController 同时协调播放服务和存储检查，职责边界可读但包含基础设施细节（include/ui/PlayerController.hpp:8）。 |
| 依赖可理解性 | 一般：clang AST 明确显示 PlayerController 同时依赖 PlaybackService 与 MediaStore，依赖事实清楚但方向存在穿层（include/ui/PlayerController.hpp:10）。 |
| 命名表意度 | 清晰：PlayerController、PlaybackService、MediaStore 均能表达角色（include/ui/PlayerController.hpp:8 / include/domain/PlaybackService.hpp:5 / include/infra/MediaStore.hpp:5）。 |
| 分层清晰度 | 混乱：media::ui 直接持有并调用 media::infra::MediaStore，UI 到基础设施的穿透使层边界不清（include/ui/PlayerController.hpp:14）。 |

总体可读性：**一般；类型和命名清楚，但 UI 对 infra 的直接依赖破坏分层可读性**

## 五、重构优先级总览

| 优先级 | finding | 排序依据 |
|---|---|---|
| P1 | FINDING-S01 | FINDING-S01：这是唯一检出的结构问题，影响主播放路径且治理成本可控，应优先处理。 |

## 六、评估方法与已知缺口

- **取证方式**：compile_commands + clang AST 语义扫描。
- **聚焦策略**：先用 compile_commands + clang AST 提取内部 record 与类型边，再核对 UI 控制器的字段和成员调用。
- **Git 历史**：未使用，历史型坏味道结论保持保守。
- **未覆盖**：compile database 只包含一个翻译单元；未覆盖条件编译组合和运行时依赖注入。
- **已知缺口**：
  - C++ AST 结论限于 compile database 成功解析的翻译单元；宏生成和未激活条件分支不在覆盖内。
- **边界**：仅做重构前诊断；完整重构设计、代码风格和 CI 门禁不在本报告范围。
