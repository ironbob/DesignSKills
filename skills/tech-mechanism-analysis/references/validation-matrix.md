# 非线性机制验证矩阵

本矩阵验证 skill 不只适用于简单同步线性数据流。每个案例包含可运行 fixture、Full JSON、真实证据行号和端到端测试。

| 案例 | 主/次类型 | 必须覆盖的非线性关系 | 重点边界/行为用例 | fixture | Full JSON / Markdown |
|---|---|---|---|---|---|
| 关键帧采样 | `data-flow` | 空轨道返回零值、左右时间越界返回端点值、区间内插值 | 空输入、左右边界；3 组 CASE ↔ ACCEPT | `examples/fixtures/keyframe-easing/src/keyframe.ts` | `examples/2026-07-23-example-analysis.json` / `.md` |
| 异步事件管线 | `data-flow` + `lifecycle` | task 并发、`await` 挂起、队列交接、结束哨兵、sink 收口 | 空流、结束哨兵传播 | `examples/fixtures/async-event-pipeline/async_pipeline.py` | `examples/2026-07-24-async-analysis.json` / `.md` |
| 订单状态机 | `state-machine` | 显式状态、合法边、拒绝守卫、转移动作、历史效果 | 非法状态边不产生副作用 | `examples/fixtures/order-state-machine/state_machine.py` | `examples/2026-07-24-state-machine-analysis.json` / `.md` |
| 反射分派 | `call-chain` + `other` | 字符串入口、`getattr` 动态解析、签名绑定、动态调用 | 动态解析失败、签名绑定失败 | `examples/fixtures/reflection-dispatch/plugin_dispatch.py` | `examples/2026-07-24-reflection-analysis.json` / `.md` |

每个 Full 示例还必须显式覆盖取消、异常、并发、背压，并分别给出
`applicable`、`uncertain` 或 `not-applicable` 结论。关键帧左右越界使用不同
`semantic_key`，对抗测试必须拒绝把二者登记为行为矛盾。

## 建模检查

### 异步

- 把任务创建、调度、挂起和完成条件写入阶段或 `handoff`。
- 记录队列、future、callback 或 channel 两端的协议。
- 明确结束、取消、异常和背压如何传播；未验证时登记 `gaps`。
- 不把源码排列顺序写成运行时先后顺序。

### 状态机

- 区分状态集合、转移条件、动作和最终可观察效果。
- 图中保留分支和终态，不把状态图压成单一路径。
- 为拒绝路径和守卫挂证据；只运行 happy path 时降低相应置信度或登记缺口。

### 反射与动态分派

- 区分请求字符串、成员解析、可调用检查、参数绑定和真实调用。
- 不用静态调用链措辞掩盖 `getattr`、注册表、依赖注入或运行时类型发现。
- 说明可发现范围、失败模式和动态边界；无法枚举全部目标时降低置信度。

## 运行

```bash
python3 scripts/test_mechanism_examples.py
```

测试依次执行：

1. 直接运行关键帧 TypeScript 的空轨道、左右越界、精确端点和区间内采样，并运行另外三个 fixture 核对可观察输出；
2. 验证每份 Full JSON；
3. 验证证据文件、行号和近邻标识符；
4. 确定性渲染 Markdown，并与已跟踪报告逐字比较；
5. 验证报告结构、回链和 Mermaid 安全子集；
6. 验证边界、行为用例、源码锚点与验收用例的双向追溯；
7. 对抗性验证矛盾记录只能比较不同入口或分支；
8. 对抗性验证矛盾记录引用的行为用例必须共享同一 `semantic_key`；
9. 缺少全局 `mmdc` 时通过固定版本 Mermaid CLI 的 npx 回退实际渲染；
10. 检查 `agents/openai.yaml` 的 Codex 展示元数据。
