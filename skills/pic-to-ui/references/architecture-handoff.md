# 条件式交接到 arch-first-code-gen

仅当 Coding Path Gate 判定 `decision.path=arch_first` 时使用本文。`direct_ui` 路径由
pic-to-ui 直接编码，不加载或模拟 arch-first。

## 职责边界

| 责任 | pic-to-ui | arch-first-code-gen |
|---|---|---|
| 解析参考截图、定义目标结构和视觉比例 | 主责 | 作为输入使用 |
| 审计当前 UI 的视觉差异 | 主责 | 使用差异及代码落点 |
| 确认角色、职责、依赖和现有仓库对齐 | 不替代 | 主责 |
| 创建或修改代码 | direct_ui 时唯一所有者 | arch_first 时唯一所有者 |
| 设计契约、架构文档、原则复核 | 收集交付证据 | 主责 |
| after 渲染、截图对比、关闭 mismatch | 主责 | 根据反馈继续改代码 |

交给 arch-first 的必须是已确认文本图、blueprint、`change-assessment.json`，repair 再附 audit。
assessment 的风险项必须解释为什么不能直接编码。

## 编码交接包

编码前提供：

- 目标工程根目录、平台、真实 UI 框架和目标屏入口；
- `text-ui-manifest.json` 与全部已确认的独立文本 UI 图；
- `blueprint.json`；
- `change-assessment.json` 及触发 arch_first 的风险项；
- repair 模式的 `repair-audit.json`、before 证据和当前代码锚点；
- 必须保留的点击、导航、状态、数据绑定、a11y 标识和测试定位符；
- 用户工作树中不得覆盖的现有改动；
- 允许修改的文件范围及共享组件/token 的潜在消费者；
- 期望的 architecture confirmation 方式；未获用户明确许可时不得自动确认。

要求 `$arch-first-code-gen` 完整遵守自己的 HARD-GATE 和产出要求。若重新检查发现可以
direct_ui，先修订 assessment 并重跑门禁，不在 arch-first 内静默降级。

repair 输入应表述为“在现有仓库中实现一个截图对齐变更，并保持已确认的职责和依赖”，而不是让 arch-first 评估或重构已有模块。若修复必须改变架构角色、跨层依赖或共享职责，让 arch-first 按正常流程重新确认；不要把架构重构偷偷包装成视觉修复。

## 技术栈兼容门

仅在 arch_first 路径检查其标准做法库是否覆盖目标栈。当前覆盖 JVM、C++、FastAPI+Vue、Swift/iOS。
若目标栈不受支持：

1. pic-to-ui 可以继续生成 blueprint 和 repair audit；
2. 不进入代码修改，不生成虚假的 `architecture_guard: passed`；
3. 请用户先扩展 `$arch-first-code-gen` 的对应标准做法库，或明确选择已支持的架构生成方案；
4. 扩展完成后再从编码交接继续。

这是一项真实阻断，不得用“沿用现有风格”一句话绕过，因为 arch-first 的角色依据、日志规范和契约校验都依赖栈知识。

## 返回包

编码阶段返回：

- 实际修改文件和代码锚点；
- `design-contract.json` 与架构文档路径；
- arch-first 三类验证/原则复核的结果和已知缺口；
- 保留行为的构建、测试或静态证据；
- 需要 pic-to-ui 重新渲染验证的 mismatch id。

把这些信息写入 `delivery.meta.architecture_guard`，设置 `mode=arch_first` 并回链 assessment
revision。Gate 2 验证设计契约与架构文档真实存在。

## 是否使用子代理

direct_ui 不使用 arch-first 或代码子代理。只有 assessment 判定 arch_first，且用户允许委派时，
才考虑一个顺序执行的代码子代理。

仅在运行环境支持且用户明确允许委派时，优先让一个**顺序执行的代码子代理**使用 `$arch-first-code-gen`，适用于：

- 涉及多个文件、多个架构角色或跨层依赖；
- 修改共享组件/token，可能影响多个消费者；
- 涉及导航、状态、数据绑定、新资源层或新依赖；
- 双端实现或需要多轮架构文档/契约校验；
- 主代理的截图与 diff 上下文很大，需要隔离编码上下文。

子代理不是并行补丁工：

1. 主代理先完成 blueprint 和 repair audit，再启动子代理。
2. 子代理是唯一代码写入者，完整使用 `$arch-first-code-gen`；主代理等待，不同时编辑目标文件。
3. 主代理收到返回包后重新渲染和验收。
4. 若仍有差异，把新增 mismatch 发回**同一子代理**继续修改，避免多个代码所有者形成架构漂移。
5. 子代理完成后，主代理仍负责运行 Gate 2、repair closure 与 Gate 3。

不要把架构“审查意见”委派给一个只读子代理后，再由 pic-to-ui 自己随意编码；这会切断设计契约与代码所有权。若使用子代理，应把架构确认和实际编码一并交给它。
