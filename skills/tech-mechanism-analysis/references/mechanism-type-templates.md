# 机制类型与链路建模

机制类型帮助选择观察角度，不是强制分类。

| 类型 | 典型信号 | 常用阶段 |
|---|---|---|
| `data-flow` | 数据被产生、传递、变换并作用于输出 | produce → flow → process → effect |
| `lifecycle` | 资源或会话经历创建、运行和释放 | init → configure → run → teardown |
| `call-chain` | 一次操作沿调用和委派传播 | entry → dispatch → core → side-effect |
| `state-machine` | 显式状态、转移条件和动作 | state → transition → action |
| `other` | 上述模型明显失真 | 自定义阶段 |

## 混合机制

真实机制可以同时具有多个视角，例如播放器既是状态机，也有帧数据流。

- `mechanism_type` 记录主类型。
- `secondary_mechanism_types` 记录必要的次类型，可为空。
- `mechanism_type_basis` 说明为什么这样建模。
- 阶段按真实执行或数据依赖顺序排列；分支、循环、异步衔接写入 `handoff`，必要时用图表达。

## Full 的结构约束

`chain_template` 与 `chain_stages[].segment` 必须：

1. 数量相同；
2. 顺序相同；
3. 每个模板阶段只对应一个阶段。

模板不适用时使用 `other` 和自定义阶段，不复制通用模板凑数。

## 每阶段字段

- `what`：代码事实——发生了什么。
- `how`：实现方式、数据结构、算法或调用点。
- `why`：设计意图或效果解释。
- `why_basis`：
  - `observed`：设计意图有 ADR、提交说明、明确文档或等价直接证据；
  - `inferred`：根据实现做出的合理推断；
  - `unknown`：代码无法证明设计意图。
- `key_structures`：关键类型、函数、字段或协议。
- `numerical`：是否包含需要工作示例的核心数值计算。
- `handoff`：到下一阶段的数据、接口、时序和隐含约定；最后一段描述最终效果。
- `evidence`：支持 what/how 的代码位置。
