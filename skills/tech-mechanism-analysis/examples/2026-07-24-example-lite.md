---
mode: lite
target: keyframe-easing
title: 关键帧缓动机制快速分析
analyzed_at: 2026-07-24
covered_files:
  - skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts
  - skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts
chain_segments: 4
numerical_examples: 4
design_observations: 2
open_questions: 0
---

# 关键帧缓动机制快速分析

## 机制概述

该机制把按时间排序的关键帧采样为一个数值，并在每次更新时写入目标对象属性。主类型是 `data-flow`；当前通过直接读取类型、实现和调用点形成中等置信度结论。

## 范围与假设

范围覆盖关键帧存储/采样和属性写入两个文件。已用 Node 原生 TypeScript 运行空轨道、左右越界和区间内采样；没有运行 TypeScript 类型检查或真实渲染循环，对调用时机的结论来自 `PropertyBinding.update` 的实现。

## 全链路

### STAGE-01 · 写入并排序关键帧

- **做了什么**：`addKeyframe` 把 `{time,value,easing}` 加入数组。
- **怎么实现**：写入后按 `time` 升序排序。
- **设计依据（inferred）**：排序数组让后续采样可以按时间扫描；这是实现推断，不是作者已确认意图。
- **交接/最终效果**：向采样阶段提供有序关键帧集合。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:20`。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:18`。

### STAGE-02 · 协议兜底并查找包围关键帧

- **做了什么**：`sampleAt` 先处理空轨道、首帧之前和末帧之后，再为区间内时间找到两侧关键帧。
- **怎么实现**：空轨道返回 `0`；`t<=first.time` 返回首值；`t>=last.time` 返回末值；其余情况线性扫描包围区间。
- **设计依据（inferred）**：先短路协议边界可避免空数组读取和区间外插值，再用简单扫描处理区间内路径；代码没有记录作者意图。
- **交接/最终效果**：兜底路径直接把 `0` 或端点值交给生效阶段；区间内路径把 `(a,b)` 交给插值阶段。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:26`、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:27`、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:29`、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:36`。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:26`、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:32`。

### STAGE-03 · 缓动插值

- **做了什么**：把查询时间归一化，应用 easing，再计算属性值。
- **怎么实现**：依次计算 `u`、`e` 和线性插值结果。
- **设计依据（inferred）**：公式直接表现了归一化、进度重映射和结果映射；这是对实现效果的推断，不是作者已确认意图。
- **交接/最终效果**：输出一个 `number`。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:40`。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:38`。

### STAGE-04 · 写入目标属性

- **做了什么**：每次 update 读取采样值并写到 `target[property]`。
- **怎么实现**：通过动态属性索引完成赋值。
- **设计依据（unknown）**：代码无法证明选择动态写入而非类型化 binding 的历史原因。
- **交接/最终效果**：目标对象属性持有当前动画值。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts:10`。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts:9`。

## 数值示例

### NUM-01 · ease-in-out 在四分之一进度处的结果

- **示例数据**：关键帧 `(0,0)`、`(1,100)`，查询 `t=0.25`。
- **计算步骤**：
  1. `u=(0.25-0)/(1-0)=0.25`。
  2. `e=4×u³=0.0625`，结果 `0+(100-0)×0.0625=6.25`。
- **结果**：属性值为 `6.25`。
- **忠实性**：步骤对应归一化、`u<0.5` 分支和最终插值，没有省略影响结果的步骤。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:52`。

### NUM-02 · 空关键帧轨道返回零值

- **示例数据**：空轨道 `frames=[]`，查询 `t=5`。
- **计算步骤**：
  1. `frames.length===0` 即 `0===0`，守卫命中。
  2. 立即返回 `0`，跳过边界判断、扫描、缓动和插值。
- **结果**：属性采样值为 `0`。
- **忠实性**：直接运行原 TypeScript 实现，验证空数组不会继续读取 `frames[0]`。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:26`。

### NUM-03 · 早于首帧时返回首值

- **示例数据**：关键帧 `(1,10)`、`(2,20)`，查询 `t=0`。
- **计算步骤**：
  1. 空轨道守卫不命中；`0<=1` 命中左边界守卫。
  2. 立即返回首关键帧值 `10`，不执行插值。
- **结果**：属性采样值为 `10`。
- **忠实性**：直接运行原 TypeScript 实现，保留 `<=` 边界语义，没有把越界行为误写成外插值。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:27`。

### NUM-04 · 晚于末帧时返回末值

- **示例数据**：关键帧 `(1,10)`、`(2,20)`，查询 `t=3`。
- **计算步骤**：
  1. 空轨道和左边界守卫不命中；取末关键帧 `(2,20)`。
  2. `3>=2` 命中右边界守卫，立即返回末值 `20`。
- **结果**：属性采样值为 `20`。
- **忠实性**：直接运行原 TypeScript 实现，保留 `>=` 边界语义，没有把越界行为误写成外插值。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:29`。

## 设计观察

### OBS-01 · 采样查找随关键帧数量线性增长

- **需求来源**：`hypothetical`。
- **会变难的需求**：在长时间线中保持大量关键帧的稳定逐帧采样成本。
- **为什么难**：每次采样从数组开头线性扫描，时间线增长会增加比较次数。
- **演进方向**：使用二分查找或复用上一次采样位置。
- **代价/影响**：修改查找阶段，并补充乱序跳转和倒放测试。
- **置信度**：`medium`；线性扫描是事实，性能需求是假设。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:32`。

### OBS-02 · 处理结果与生效接口固定为 number

- **需求来源**：`hypothetical`。
- **会变难的需求**：插值颜色、矩阵或携带采样元数据。
- **为什么难**：`sampleAt` 返回 `number`，下游直接写入动态属性。
- **演进方向**：引入可类型化的采样值和 binding 适配层。
- **代价/影响**：影响采样返回类型、调用方和序列化兼容。
- **置信度**：`medium`；接口事实明确，结构化值需求是假设。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts:10`。

## 已知缺口

- 未运行真实渲染循环，报告不评价帧调度和并发行为。
