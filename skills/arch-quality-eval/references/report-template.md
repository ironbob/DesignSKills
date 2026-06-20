# report.md 模板（模块 D）

> 配合 `arch-quality-eval` 的 Checklist 第 9 步使用。`report.md` 是 `findings.json` 的人读渲染，二者必须一致（`validate_contract.py` 对账）。frontmatter 字段对齐 `validate_report.py` 的 R-F 规则。

## Frontmatter（必填，R-F 硬卡）

```yaml
---
module: order-service                 # 模块名（与 findings.json 一致）
title: 订单服务 架构质量诊断
language: JVM                         # JVM | C++
analyzed_at: 2026-06-20
covered_files:                        # 覆盖文件集合（非空）
  - src/main/java/com/x/order/OrderService.java
  - src/main/java/com/x/order/OrderController.java
  - src/main/java/com/x/promotion/PromotionService.java
conventions_fed: false                # 是否喂入项目规约
no_go_threshold: 1                    # critical ≥ 此值 → no-go
verdict: no-go                        # go | no-go（与 findings.json summary 一致）
critical_count: 1                     # critical 数（与 findings.json summary 一致，R-G 卡）
major_count: 2
minor_count: 1
cpp_limitation_noted: false           # C++ 时为 true
open_questions: 0                     # ⚠ 未确认 数量
status: draft
---
```

> frontmatter 的 `covered_files` 用 YAML 列表；正文「评估范围」节再用人话概述。

## 正文章节结构（标题用这些关键词，脚本按关键词定位节）

### 一、评估范围（覆盖 module A）
- 路径 + 覆盖文件集合概述（N 个文件 / 涉及包或目录）。
- 语言与结构识别（JVM 包结构 / C++ 命名空间+目录）；C++ 标注能力受限。
- 是否喂入规约（喂入则附 `convention_rules` 清单；未喂入则明说「只跑通用准则」）。
- 一句话模块职责（它声称做什么，非「应有架构」）。

### 二、go/no-go 门禁结论（放最前，先给决策信号）
- 显式 verdict：`✅ go` / `⛔ no-go`。
- critical 数 / 阈值；列出所有 critical 项（id + 标题 + 一句依据）。
- 一句话结论：要不要重构、卡在哪。

### 三、架构坏味道清单（覆盖 module B；R-C 卡核心类齐全 + R-L1 回链 + R-S 分级 + R-P 原理 + R-PR 改进/优先级）

**核心坏味道覆盖矩阵**（每条核心类二分显式：✅已检出 / ⬜未检出）：

| 核心坏味道 | 判定 | 证据锚点 |
|-----------|------|---------|
| 循环依赖 circular-dependency | ✅ FINDING-S01 | OrderService.java:42 |
| God Class / God Package | ✅ FINDING-S02 | OrderService.java:1 |
| 跨层调用 cross-layer | ✅ FINDING-S03 | OrderController.java:33 |
| 霰弹式修改 shotgun-surgery | ⬜ 未检出（N/A） | — |
| 不恰当暴露 inappropriate-exposure | ✅ FINDING-S04 | OrderService.java:120 |

> 扩充坏味道（门面滥用/平行继承/中间人/发散变化/特性依恋/不稳定依赖）：检到即报同表，未检出的可省略。

**逐条 finding 详述**（每条：标题 + 分级依据 + 证据 file:line + 违反原理 + 影响 + 改进方向 + 修复成本 + 优先级）：

```
#### FINDING-S01 · order 与 promotion 包级循环依赖 · 🔴 critical
- 证据：order→promotion `OrderService.java:42`（import promotion.PromotionService）；
       promotion→order `PromotionService.java:18`（import order.OrderRepository）。
- 违反原理：单向依赖原则。
- 影响：两个包无法独立编译/部署/演进，任一改动相互阻塞，是重构主要阻塞点。
- 分级依据：包级循环依赖 → critical（阻塞重构）。
- 改进方向：抽共用领域模型到独立包，或用事件/接口反转依赖方向（完整方案留重构阶段）。
- 修复成本：high　优先级：P1（先解循环，它是 God Class 拆分的先决条件）。
```

（其余 finding 同此格式。）

### 四、项目规约违规（仅 conventions_fed=true 时；R-V 卡）

- 列出喂入的 `convention_rules`（id + 规约）。
- 逐条规约二分：✅检出违规（→ FINDING-Cxx）/ ⬜未检出。
- 逐条违规 finding 详述（convention_violated 指向规约 id）。

> conventions_fed=false 时**本节整节省略**，且不得出现 `axis: convention` 的结论（R-V）。

### 五、架构可读性（覆盖 module C；readability 四轴 + 总体）
- 四轴逐条结论 + 证据锚点（职责清晰度 / 依赖可理解性 / 命名表意度 / 分层清晰度）。
- 总体可读性判断（清晰/一般/混乱）+ 最影响可读性的一点。
- 严重的可读性问题可在此单列 FINDING-Rxx（轻度只写结论）。
- **不含** lint 能查的代码风格（缩进/命名格式/import 顺序）。

### 六、重构优先级总览（覆盖 module D P0）
- 按 P1/P2/P3 排出「先改哪个收益最大」，每条给排序依据（影响面 × 阻塞 × 成本）。
- 点明先决关系（如「先解 FINDING-S01 循环依赖，才能安全拆 FINDING-S02 God Class」）。
- 给一个建议的改动顺序（3-5 步，指方向不写完整方案）。

### 七、评估方法与已知缺口
- 评估方法：用了 LSP 还是 rg 降级；聚焦策略（热点优先/分层扫描）+ 舍弃了什么（防「看似全覆盖实则抽样」）。
- C++（如适用）：结构/依赖分析受限说明。
- 已知缺口：逐条列 `⚠ 未确认` 的项 + 无法定位的结论（与 `open_questions` 计数对账，R-U）。
- 越界说明：本报告只做重构前诊断，不提完整重构方案/不卡 CI/不做 lint（指向 PRD §5）。

## 端到端示例

见 `examples/2026-06-20-example-report.md`（JVM OrderService 模块：1 critical 循环依赖 + 2 major + 1 minor，no-go）。该示例必须三道门全过。

## 写作纪律（与 `severity-and-priority.md §四` 一致）

- 每条结论回链 `file:line`，找不到的标 `⚠ 未确认` + 登记缺口。
- 分级用客观依据（爆炸半径/阻塞/可增量/证据强度），禁「感觉像 critical」。
- smell finding 必点名通用设计原理；convention finding 必点名规约 id。
- 改进只指方向，不写完整重构方案（超范围，越界拉回）。
- 不混入 lint；不编造证据。
