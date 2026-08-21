# Linear 风格 · 证据

## 采样范围

- `source-product`: Linear
- `source-version`: March 2024 foundational UI redesign, cross-checked with current docs
- `platforms`: Web, macOS, Windows
- `collected-at`: 2026-08-21
- `evidence-grade`: B+
- `representation`: neutral high-density Linear profile with one configurable accent

## 官方来源

| ID | 官方来源 | 版本/日期 | 支持的结论 |
| --- | --- | --- | --- |
| O-LN-01 | [How we redesigned the Linear UI](https://linear.app/now/how-we-redesigned-the-linear-ui) | 2024-03-28 | 降噪、层级/密度、inverted-L chrome、跨平台、主题生成、Inter/Inter Display、布局压力测试 |
| O-LN-02 | [Welcome to the new Linear](https://linear.app/changelog/2024-03-20-new-linear-ui) | 2024-03-27 | 新侧栏/导航头/Inbox、亮暗主题、对比度、Magic Blue 与可定制主题 |
| O-LN-03 | [Select issues](https://linear.app/docs/select-issues) | 2026-08 采样 | hover/highlight、选中、多选、Esc、命令菜单、右键与键盘路径 |
| O-LN-04 | [Search](https://linear.app/docs/search) | 2026-08 采样 | `/`、Cmd/Ctrl+F、最近项目与侧栏入口并存，证明键盘优先但不只依赖键盘 |

## observed

- `O-LN-01` 2024 重设计明确调整 sidebar、tabs、headers、panels，以减少噪声并提高导航层级和密度。
- `O-LN-01` 视觉系统由 base color、accent color、contrast 生成，并支持亮色、暗色、自定义和高对比配置；固定紫色不是跨工作区 invariant。
- `O-LN-01` 标题使用 Inter Display、正文继续使用 Inter；布局覆盖 list、board、timeline、split、fullscreen，而不是单一三栏模板。
- `O-LN-03`、`O-LN-04` 鼠标、快捷键、命令菜单和上下文菜单是同一动作系统的多个入口；Esc 和焦点态属于真实交互，不是装饰 kbd chip。

## derived

- `D-LN-01` 本包的默认紫 `#5E6AD2` 是可辨识的 Linear-inspired 默认配置，不是官方声明的唯一 accent；实现必须允许替换为单一 accent 变体。
- `D-LN-02` 26-32px 控件、紧凑行高、低圆角和 100-120ms 反馈来自视觉归纳，非公开官方 Token。
- `D-LN-03` “弱 accent 选中底 + 中性 hover + 实色分层”是多个官方样本的共同关系，alpha 需按主题对比度调节。

## adapted

- `A-LN-01` 目标没有命令系统或快捷键时不绘制假的 ⌘K/kbd；保留真实鼠标入口与可发现性。
- `A-LN-02` 目标数据更密或触控优先时扩大热区，但保持同产品内相对紧凑。
- `A-LN-03` 目标不是 issue tracker 时不迁移 issue、cycle、project、triage 等对象或 inverted-L 结构。

## 视觉覆盖

| 默认骨架 | 交互状态 | 浮层 | 异常/边界 | 窄窗 | 主题 |
| --- | --- | --- | --- | --- | --- |
| 官方多视图：有 | 选择/多选/Esc：有；disabled/focus 样本不足 | command/context：行为有 | 多视图压力测试：有；错误态不足 | 跨平台说明：有；窄窗图不足 | 亮/暗/自定义/高对比：有 |

## 证据缺口与禁止断言

- 官方文章解释系统生成方式但未公布本包使用的全部 hex、px、radius 和 duration；这些数值均为 derived。
- 2024 基线之后 Linear 持续迭代；没有重新采样前不得把每个组件称为 2026 当前逐像素实现。
- 不得把“固定品牌紫”“必须三栏”“必须显示 ⌘K”写成 Linear 的不可变规则。

## 刷新条件

- Linear 发布新的 foundational redesign、主题生成或导航框架；官方 Docs 中命令、搜索、选择模型发生改变。
