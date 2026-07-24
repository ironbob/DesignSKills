# 设计债审计

设计债是当前设计在某个具体演进需求下产生的额外成本，不是正确性 bug，也不是抽象的“扩展性差”。

## 需求来源

每条设计债必须标明 `requirement_source`：

- `user`：用户明确提出；
- `roadmap`：产品或技术路线图；
- `issue`：仓库 issue、任务或已知请求；
- `code-evolution`：代码中已经出现的演进信号，例如重复适配或兼容分支；
- `hypothetical`：分析者构造的合理场景。

`hypothetical` 只能说明“如果要做 X，会产生 Y 成本”，不能写成团队一定需要 X。

## 两个观察轴

- `architecture`：职责边界、依赖方向、耦合、存储或协议暴露。
- `logic`：算法、数据结构、状态表达、数据流假设、数值范围。

两轴允许为空。不要为了覆盖而制造债务。

跨阶段问题设置 `cross_stage=true`，例如格式、单位、接口或时序约定横跨两个阶段。

## 每条必填内容

- `hard_requirement`：具体演进场景。
- `why_hard`：当前设计导致成本的位置和原因。
- `evolution_direction`：解除约束的方向，不展开完整迁移方案。
- `cost_impact`：涉及的阶段、数据、接口、兼容性或验证成本。
- `cost_quantification`：列出受影响阶段、文件、模块、改动量级及其代码依据。
- `confidence`：`high` / `medium` / `low`，表示结论证据可信度，不表示严重程度。
- `confidence_basis`：为什么给出该置信度。
- `evidence`：支持当前设计事实的代码位置。

## Lite

最多给 3 条与用户目标最相关的设计观察；需求全是 `hypothetical` 且相关性低时可以不输出。

## Full

检查架构、逻辑和跨阶段衔接。某一轴没有发现时在报告明确说明。
