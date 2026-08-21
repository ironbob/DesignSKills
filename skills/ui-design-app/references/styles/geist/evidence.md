# Geist 风格 · 证据

## 采样范围

- `source-product`: Vercel Geist Design System and Vercel dashboard profile
- `source-version`: current Geist documentation snapshot
- `platforms`: Web
- `collected-at`: 2026-08-21
- `evidence-grade`: B+
- `representation`: monochrome Vercel-dashboard profile; not the complete Geist component/theme space

## 官方来源

| ID | 官方来源 | 版本/日期 | 支持的结论 |
| --- | --- | --- | --- |
| O-GE-01 | [Geist Design System](https://vercel.com/geist/stack) | 2026-08 采样 | 官方 foundations、components、Geist Sans/Mono、开发者工具定位 |
| O-GE-02 | [Geist Colors](https://vercel.com/geist/colors) | 2026-08 采样 | 10 个色阶；背景、组件背景、边框、高对比背景、文字/图标的语义分工 |
| O-GE-03 | [Geist Typography](https://vercel.com/geist/typography) | 2026-08 采样 | size/line-height/letter-spacing/weight 的组合类，heading/copy/label/button 层级 |
| O-GE-04 | [Vercel Web Interface Guidelines](https://vercel.com/design/guidelines) | living document | 键盘、focus-visible、热区、全部状态、tabular nums、冗余状态线索、细边与分层阴影 |
| O-GE-05 | [Theme Switcher](https://vercel.com/geist/theme-switcher) | 2026-08 采样 | Light/System/Dark 标准控制、disabled 与可访问名称 |

## observed

- `O-GE-02` 完整 Geist 不是纯黑白系统：它包含 gray/alpha/blue/red/amber/green/teal/purple/pink 等 10 个色阶，每个色阶有明确语义位置。
- `O-GE-02` Background 1/2、Color 1-3、4-6、7-8、9-10 分别服务默认背景、组件状态、边框、高对比背景和文字/图标。
- `O-GE-03` Geist 排版是组合系统，不是“全局 14px + mono”；mono/tabular 主要服务代码、ID 和可比较数值。
- `O-GE-04` 键盘可达、可见焦点、非颜色唯一状态、稳定骨架、空/稀疏/密集/错误态和精确边缘属于可靠实现要求。

## derived

- `D-GE-01` 本包把 Vercel dashboard 常见的中性骨架、黑白反转主操作和 mono 点缀收敛为一个“monochrome profile”；它是 Geist 的一个配置，不是完整 Geist。
- `D-GE-02` 32px 控件、36-40px 表格行、6-8px 圆角及当前 hex 是离线参考实现，未直接绑定官方 Geist Core 变量。
- `D-GE-03` 淡彩 status pill 是语义色阶的应用之一；官方系统并未规定颜色只能用于 pill。

## adapted

- `A-GE-01` 离线 demo 使用系统字体回退；生产实现可加载官方 Geist Sans/Mono，并处理字体加载与 fallback。
- `A-GE-02` 目标产品可以按 Geist 语义色阶使用状态色，但默认 dashboard profile 仍保持大面积中性，避免变成彩色营销界面。
- `A-GE-03` 主按钮是否黑白反转由所选 profile 和功能层级决定；不能把它描述为所有 Geist 组件的官方强制规则。

## 视觉覆盖

| 默认骨架 | 交互状态 | 浮层 | 异常/边界 | 窄窗 | 主题 |
| --- | --- | --- | --- | --- | --- |
| foundation/components：有 | hover/active/border/focus/disabled：有 | 组件库：有 | empty/sparse/dense/error 要求：有 | 指南要求：有；本包样本部分 | Light/System/Dark：有 |

## 证据缺口与禁止断言

- 当前 token hex 与组件 CSS 没有从 Geist Core 包自动同步，属于 derived；不得宣称为官方 Token 镜像。
- 不得说“Geist 只有黑白灰”“彩色只能用于状态 pill”或“所有主按钮必须黑色”。
- Vercel 部署、域名、分支等数据对象属于业务，不是 Geist 身份。

## 刷新条件

- Geist foundations/changelog 发生破坏性更新；官方颜色或排版 Token 可机器读取；Vercel dashboard 视觉 profile 重构。
