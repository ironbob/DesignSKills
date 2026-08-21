# Figma 风格 · 证据

## 采样范围

- `source-product`: Figma Design UI3
- `source-version`: UI3 final transition baseline, April 30 2025
- `platforms`: Web and desktop editor
- `collected-at`: 2026-08-21
- `evidence-grade`: B+
- `representation`: docked resizable panels + bottom toolbar; floating panels only in documented contexts

## 官方来源

| ID | 官方来源 | 版本/日期 | 支持的结论 |
| --- | --- | --- | --- |
| O-FG-01 | [Inside the redesigned Figma, where your work takes center stage](https://www.figma.com/blog/behind-our-redesign-ui3/) | 2024-06-26 | 画布优先、可折叠面板、底部 slim toolbar、输入背景/边框/圆角、可选 labels、属性重组 |
| O-FG-02 | [Figma on Figma: our approach to designing UI3](https://www.figma.com/blog/our-approach-to-designing-ui3/) | 2024-10-01 | 用户反馈后恢复 docked panels；浮动只保留在 Minimize UI、Slides grid、FigJam 等上下文 |
| O-FG-03 | [Making the move to UI3](https://www.figma.com/blog/making-the-move-to-ui3-a-guide-to-figmas-next-chapter/) | 2025-03-25 / 04-30 transition | UI2 退出、逻辑布局控件、Minimize UI、Actions menu、底部工具栏、Dev Mode 入口 |
| O-FG-04 | [Figma 2024: we shipped it, you shaped it](https://www.figma.com/blog/figma-2024-we-shipped-it-you-shaped-it/) | 2024-12-04 | “fixed panels are back”、面板 docked/resizable、底部工具栏与 Actions menu |

## observed

- `O-FG-01` UI3 的主原则是让作品/画布居中，常用工具保持可达；面板可折叠，工具栏移到画布底部。
- `O-FG-02`、`O-FG-04` 正式 UI3 的默认 Design 编辑器不是“三块永久浮板”：左右面板停靠且可调整宽度，浮动仅在特定模式/产品出现。
- `O-FG-01` UI3 给输入、下拉增加可见背景/边框与圆角，并允许图标标签开关以平衡新手可发现性与专家效率。
- `O-FG-03` layout 相关控制被更合逻辑地组合；Minimize UI 保留工具栏并按选择显示属性面板；Actions menu 延续快速动作入口。

## derived

- `D-FG-01` 11-12px 信息、24-28px 控件、选择蓝、手柄和数值排版是当前包的视觉归纳，非 Figma 公开 Token。
- `D-FG-02` 中性工具 active 与蓝色对象 selected 分离，是专业编辑器样本归纳；具体灰/蓝 alpha 需按画布主题校准。
- `D-FG-03` 面板宽度、阴影、圆角和断点为离线 demo 适配，不等于 Figma 当前窗口的测量值。

## adapted

- `A-FG-01` 非画布产品保留自身布局，只迁移紧凑专业 chrome、精确数值、选择语义和即时反馈。
- `A-FG-02` 小控件保持可见尺寸紧凑，但点击热区不得低于目标平台最低要求；需要时提供标签或 tooltip。
- `A-FG-03` 只有目标存在工具模式时才采用单键工具；已有输入焦点时必须抑制单键切换。

## 视觉覆盖

| 默认骨架 | 交互状态 | 浮层 | 异常/边界 | 窄窗 | 主题 |
| --- | --- | --- | --- | --- | --- |
| 正式 UI3：有 | label/minimize/selection：部分；disabled/focus 缺 | Actions/menu：有 | 多属性/复杂度讨论：有；错误态缺 | Minimize UI：有 | 主题存在；同状态成对样本不足 |

## 证据缺口与禁止断言

- 官方文章没有发布 UI3 全量颜色、尺寸、圆角或动效 Token；本包所有 px/hex/duration 均为 derived。
- 不得再把 2024 beta 的三块浮动面板写成正式 UI3 默认签名。
- Figma 图层、组件、V/R/T 工具和画布手柄属于创作工具原型，不适合普通列表/表单产品。

## 刷新条件

- Figma 发布 UI4 或改变 Design 编辑器的 dock/minimize/toolbar 模型；Actions、属性面板或画布选择语义重构。
