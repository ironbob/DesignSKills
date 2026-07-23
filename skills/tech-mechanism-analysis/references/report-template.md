# analysis.md 模板（模块 D）

> 配合 `tech-mechanism-analysis` 的 Checklist 第 9 步使用。`analysis.md` 是 `analysis.json` 的人读渲染，二者必须一致（`validate_contract.py` 对账）。frontmatter 与章节关键词对齐 `validate_report.py` 的规则。

## Frontmatter（必填）

```yaml
---
target: keyframe-easing                      # 机制名（与 analysis.json 一致）
title: 关键帧缓动机制 深度分析
mechanism_type: data-flow                    # 与 json 一致
languages: [TypeScript]                      # 与 json 一致
analyzed_at: 2026-07-23
covered_files:                              # 覆盖文件集合（非空，与 json 一致）
  - src/keyframe.ts
  - src/track.ts
chain_segments: 4                           # 链路段数（与 json chain_stages 一致）
numerical_examples: 1                       # 数值举例数（与 json 一致）
defects_arch: 1                             # 架构轴缺陷数（与 json 一致）
defects_logic: 1                            # 逻辑轴缺陷数（与 json 一致）
open_questions: 0                           # ⚠ 未确认 数量
status: draft
---
```

## 正文章节结构（标题用这些关键词，脚本按关键词定位节）

### 一、机制概述（覆盖模块 A）
- 机制对象 + 一句话职责。
- **机制类型 + 判定依据**（如「数据流型，依据：关键帧被产生→存储→按时间查找→缓动插值→写入渲染属性」）。
- 套用的链路模板（`产生→流转→处理→生效`）。
- 覆盖文件集合概述（N 个文件 / 涉及哪些目录）。
- 多语言技术栈 + **各语言精度**（high/medium/low）。

### 二、全链路分段讲解（覆盖模块 B；逐段 what/how/why + 证据 + 跨段衔接）
- 按链路模板逐段（如「产生 / 流转 / 处理 / 生效」），每段：
  - 做了什么、怎么实现、为什么这么设计、关键数据结构 / 算法 / 调用点。
  - 证据 `file:line`。
  - **跨段衔接**：与下一段的隐含约定（数据格式 / 接口 / 时序）。
- 链路可视化（P2，可选）：内嵌 Mermaid 时序 / 状态 / 流程图，节点回链证据。
- 某段不适用时显式声明原因，不静默省略。

> 找不到的结论标 `⚠ 未确认` + 登记缺口，**禁止编造**。

### 三、数值操作工作举例（★ 覆盖模块 B 签名能力）
- 每个 `numerical=true` 段 ≥1 个工作举例，含：
  - 运算名 + 示例数据（适度规模，非平凡）。
  - **逐步实际运算**（每步可核）+ 结果。
  - 是否做了**代码翻译**（如转 Python 求值）+ **faithfulness 声明**（运算与原代码一致）。
  - 证据 `file:line`。
- 全链路无数值段时写「本机制未识别到数值计算环节」。

### 四、架构问题（覆盖模块 C · 架构轴）
- 逐条 `DEBT-ARCH-NN` + 所属链路段 + 四要素（会变难的需求 + 为什么难 + 演进方向 + 代价/影响）+ 证据。
- 跨段衔接缺陷标注 `cross_stage`。
- 无则写「本机制未识别到架构轴设计债」。
- **不分级、不下 go/no-go、不找 bug、不给完整重构方案**。

### 五、逻辑问题（覆盖模块 C · 逻辑轴）
- 逐条 `DEBT-LOGIC-NN` + 所属链路段 + 四要素 + 证据。
- 无则写「本机制未识别到逻辑轴设计债」。

### 六、已知缺口
- 逐条 `⚠ 未确认` 项 + 无法定位的结论（与 `open_questions` 计数对账）。
- 多语言精度差异说明（low/medium 的结论更保守）。
- 越界说明：本报告只做机制深度分析（全链路理解 + 数值举例 + 双轴设计债），不做 bug / 整体架构 / 重构决策 / 业务分析（指向对应 skill）。

## 写作纪律

- 每段 / 每数值举例 / 每条缺陷回链 `file:line`，找不到标 `⚠ 未确认` + 缺口。
- 数值举例运算与原代码一致，必要时代码翻译求值，结果可核。
- 缺陷四要素齐全，需求具体；**不打分级、不写 bug**。
- 不混 lint；不编造证据。
- banned 词：「体验好 / 功能完善 / 适当处理 / 待定 / 很重要 / 扩展性强 / 灵活性好」等空话——改成具体可核说法。

## 端到端示例

见 `examples/2026-07-23-example-analysis.md`（关键帧缓动机制）。该示例必须四道门全过。
