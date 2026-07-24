---
mode: full
target: "keyframe-easing"
title: "keyframe-easing 技术机制深度分析"
mechanism_type: "data-flow"
languages: ["TypeScript"]
analyzed_at: "2026-07-23"
covered_files:
  - "skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts"
  - "skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts"
chain_segments: 4
numerical_examples: 1
defects_arch: 2
defects_logic: 1
open_questions: 2
---

# keyframe-easing 技术机制深度分析

## 机制概述

- **模式**：full。
- **一句话职责**：在时间线上对一个数值属性做带缓动的关键帧插值，并在每帧把结果写到渲染对象的属性上。
- **主机制类型**：`data-flow`。
- **次机制类型**：无。
- **类型依据**：关键帧被产生并存入时间线 → 播放时按时间查找关键帧对 → 缓动插值求值 → 写入渲染属性，是典型的 产生→流转→处理→生效 数据流。
- **链路模板**：`produce` → `flow` → `process` → `effect`。

### 范围确认

- **SCOPE-01 · initial · 2026-07-23**：示例任务中用户明确确认机制对象、候选文件、主类型和一句话职责；候选文件：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts`、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts`。

### 工具与证据置信度

- **TypeScript · medium**：已读取类型、实现和直接调用点，并对核心公式做等价求值；示例未运行 TypeScript 类型检查或测试；工具：direct code reading、text search、equivalent numerical evaluation。

## 全链路

### stage-produce · 产生：关键帧存入扁平时间线

- **阶段标识**：`produce`。
- **做了什么**：调用方通过 addKeyframe(time,value,easing) 追加一个关键帧；机制把它 push 进数组并按 time 升序排序。
- **怎么实现**：存储是 KeyframeTrack 内一个私有数组 frames: Keyframe[]，每帧 {time,value,easing}；写入后 sort 保证升序。
- **设计依据（inferred）**：排序数组让后续采样可以按时间顺序扫描；这是根据实现结构推断的设计取舍，源码未记录作者意图。
- **关键结构**：`Keyframe interface`、`KeyframeTrack.frames: Keyframe[]`、`addKeyframe`。
- **交接/最终效果**：以升序 Keyframe[] 交给读取段，约定按 time 单调递增；无轨道维度。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:20`（sort establishes ascending handoff order）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:15`（frames flat list storage）、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:18`（addKeyframe push and sort）。

### stage-flow · 流转：按时间扫描定位关键帧对

- **阶段标识**：`flow`。
- **做了什么**：sampleAt(t) 在排序数组里线性扫描，找到 t 落在哪两个相邻关键帧之间。
- **怎么实现**：从 i=0 起逐个比较 frames[i+1].time < t，停在 t 所属区间，取出包围对 (a,b)。
- **设计依据（inferred）**：线性扫描与已排序数组形成简单的区间定位实现；这是实现效果推断，不代表作者已确认的取舍。
- **关键结构**：`sampleAt linear scan`、`surrounding pair (a,b)`。
- **交接/最终效果**：把一对 (a,b) 关键帧交给处理段，约定 a.time <= t <= b.time。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:36`（frames index selects b next to a）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:32`（while scan surrounding pair）。

### stage-process · 处理：归一化 → 缓动 → 线性插值

- **阶段标识**：`process`。
- **做了什么**：把 t 在 (a,b) 区间归一化为进度 u，用 easing 曲线把 u 映射为缓动进度 e，再在 a.value/b.value 间线性插值。
- **怎么实现**：u=(t-a.time)/(b.time-a.time)；e=applyEasing(a.easing,u)；result=a.value+(b.value-a.value)*e。
- **设计依据（inferred）**：归一化把任意区间映射到 [0,1]，缓动函数重映射进度，最后线性插值回属性值；该数学作用可由公式直接观察。
- **关键结构**：`applyEasing`、`normalize progress u`、`lerp a.value+(b.value-a.value)*e`。
- **交接/最终效果**：返回一个 number（插值结果）给生效段，不带类型/元数据。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:40`（return interpolated value using easing）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:38`（normalize progress u）、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:39`（applyEasing call）、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:40`（lerp interpolate value）。

### stage-effect · 生效：写入渲染对象属性

- **阶段标识**：`effect`。
- **做了什么**：PropertyBinding.update 每帧调用 sampleAt 取值，直接赋值到 target[property]。
- **怎么实现**：const v = track.sampleAt(time); (this.target as any)[this.property] = v;。
- **设计依据（unknown）**：该写入使采样值成为目标对象的可观察属性；源码没有记录选择动态属性写入的历史原因。
- **关键结构**：`PropertyBinding.update`、`target[property] = v`。
- **交接/最终效果**：最终效果是 target[property] 在每次 update 后持有当前采样值，供后续渲染代码读取。
- **交接证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts:10`（assignment makes sampled value observable on target）。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts:9`（sampleAt pull value）、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts:10`（direct property write）。

### 链路图

```mermaid
flowchart LR
  produce["产生 addKeyframe"]
  flow["流转 sampleAt 扫描"]
  process["处理 缓动+插值"]
  effect["生效 写入属性"]
  produce -->|"升序 Keyframe[]"| flow
  flow -->|"包围对 (a,b)"| process
  process -->|"插值 number"| effect
```

## 数值示例

### NUM-01 · ease-in-out 三次缓动插值（对应 sampleAt 的处理段）

- **所属阶段**：`stage-process`。
- **示例数据**：关键帧 a=(time=0.0, value=0, easing=ease-in-out)、b=(time=1.0, value=100)；查询 t=0.25。
- **计算步骤**：
  1. 归一化进度 u = (0.25-0.0)/(1.0-0.0) = 0.25
  2. applyEasing('ease-in-out', 0.25)：u<0.5 分支 → e = 4×u³ = 4×0.25³ = 4×0.015625 = 0.0625
  3. 线性插值 result = a.value + (b.value-a.value)×e = 0 + (100-0)×0.0625 = 6.25
- **结果**：6.25（在 t=0.25 处；缓动使值远低于线性插值的 25，体现 ease-in-out 前慢后快）。
- **代码翻译**：将 keyframe.ts:52 的 cubic 分支译为 Python 求值：e = 4*u**3 if u<0.5 else 1-(-2*u+2)**3/2；代入 u=0.25 → 0.0625；再按 line 40 做 lerp → 6.25。
- **忠实性**：运算与原代码 sampleAt(line 38-40) + applyEasing(line 52) 逐行对应；已转 Python 实际运行验证结果=6.25；保留了归一化、u<0.5 分支判断与 lerp，未省略任何影响结果的步骤。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:38`（normalize progress u）、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:52`（cubic ease-in-out branch u<0.5）。

## 架构设计债

### DEBT-ARCH-01 · 扁平时间线无轨道维度

- **所属阶段**：`stage-produce`。
- **需求来源**：`hypothetical`。
- **会变难的需求**：支持多轨道关键帧交错 + 冲突仲裁（如多条动画轨道在同一属性上叠加或抢占）。
- **为什么难**：frames 是单条按 time 排序的扁平 Keyframe[]（keyframe.ts:13-15），没有 track 维度；要做多轨道需给 Keyframe 加 track 字段、按 (track,time) 索引、再加一层冲突仲裁，产生段/流转段/处理段都要改。
- **演进方向**：引入 track 维度：Keyframe 增 track 字段或改 Map<track, Keyframe[]>；sampleAt 按 (track,time) 查找；冲突走优先级或混合仲裁层。
- **代价/影响**：涉及 produce/flow/process 三段；存储格式需迁移既有时间线；中等改动面。
- **量化范围**：阶段 3 个（`stage-produce`、`stage-flow`、`stage-process`）；文件 1 个（`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts`）；模块 1 个（`KeyframeTrack`）；量级 `medium`；当前单文件中的存储、区间定位和插值三段共同依赖扁平 frames，至少需要同时调整三个阶段。
- **结论置信度**：`medium`；单列表结构是直接代码事实，但多轨道需求是用于评估演进成本的假设场景。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:6`（Keyframe fields time value easing）、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:15`（frames flat list storage）。

### DEBT-ARCH-02 · 生效段直接写属性，处理→生效之间无中间抽象

- **所属阶段**：`stage-effect`；跨阶段。
- **需求来源**：`hypothetical`。
- **会变难的需求**：支持非数值/结构化目标（颜色、变换矩阵）或携带每帧元数据（如不连续标志、触发事件）。
- **为什么难**：PropertyBinding.update 把 sampleAt 返回的 number 直接 target[property]=v（renderer.ts:9-10），处理段与生效段之间没有 binding 中间层；颜色/矩阵需不同写入逻辑，元数据无处承载——这是跨段（process→effect）衔接的设计债。
- **演进方向**：引入 Binding 抽象层：sampleAt 返回带类型/元数据的 SampledValue，Binding 按目标类型写入（数值/颜色/矩阵）并处理元数据。
- **代价/影响**：跨段改动 process→effect 接口；新增 Binding 层及目标类型分发；涉及调用方兼容。
- **量化范围**：阶段 2 个（`stage-process`、`stage-effect`）；文件 2 个（`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts`、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts`）；模块 2 个（`KeyframeTrack`、`PropertyBinding`）；量级 `large`；返回值契约和写入端横跨两个阶段、两个文件及两个模块，且需要调用方兼容迁移。
- **结论置信度**：`medium`；number 返回值和动态属性写入是直接证据；结构化目标需求是用于分析接口演进成本的假设。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts:10`（direct property write no binding）。

## 逻辑设计债

### DEBT-LOGIC-01 · 缓动是封闭枚举 + switch 硬编码

- **所属阶段**：`stage-process`。
- **需求来源**：`hypothetical`。
- **会变难的需求**：支持用户自定义缓动曲线（三次贝塞尔控制点、弹簧物理、样条曲线）。
- **为什么难**：Easing 是封闭枚举，applyEasing 用 switch 把每条曲线硬编码（keyframe.ts:46-53）；新增曲线要改枚举 + switch + 序列化，调用方无法注入函数或参数化的曲线数据。
- **演进方向**：把 Easing 从封闭枚举改为数据/函数：如 {type:'cubic-bezier',p1x,p1y,p2x,p2y} 或 (u)=>number 函数 + 注册表；applyEasing 改为按数据求值/查表调用。
- **代价/影响**：需改 Easing 类型定义 + applyEasing 实现 + 关键帧序列化；涉及类型与数据兼容。
- **量化范围**：阶段 1 个（`stage-process`）；文件 1 个（`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts`）；模块 2 个（`Easing`、`applyEasing`）；量级 `medium`；核心改动集中在一个处理阶段和一个文件，但会改变公开类型及其序列化兼容约定。
- **结论置信度**：`medium`；封闭联合类型和 switch 是直接证据；自定义曲线需求为假设场景，仓库没有路线图证据。
- **证据**：`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:47`（switch easing closed enum）、`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:52`（cubic ease-in-out branch u<0.5）。

## 跨阶段衔接

`DEBT-ARCH-02` 涉及跨阶段约定。

## 已知缺口

- ⚠ 未确认：示例为 TypeScript 单语言，未演示多语言精度差异；调用边为直接读码，未走 LSP
- ⚠ 未确认：当前验证环境未安装 mmdc；Mermaid 已通过安全子集结构检查，但未执行实际 SVG 渲染
