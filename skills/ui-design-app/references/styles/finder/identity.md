# Finder 风格 · 迁移身份

> 证据边界：以 macOS Tahoe 26 Finder/HIG 为版本截面；官方支持结构与系统材质方向，CSS 数值为 derived。详见 `evidence.md`。

## 风格命题

以 macOS 原生层级、系统蓝和克制状态表达，让现有功能看起来属于桌面系统；不是把产品改成文件管理器。

## invariant

- 系统蓝只承担选中、菜单高亮、主操作、焦点和进行中；默认开启与打开态不长期占蓝。
- chrome、浮层与内容画布有清楚的系统材质职责；当前平台允许侧栏 Liquid Glass，发丝边、柔影、无彩色发光。
- 控件静态、热区可靠、文字和图标采用 macOS 紧凑但可读的比例。
- 选中、hover、拖拽目标、窗口失活使用不同语言；状态不只靠颜色。
- 菜单若为自绘，遵守 NSMenu 的三列对齐、键盘路径、子菜单和蓝底白字高亮。

## adaptive

- vibrancy 强度、同屏材质层数和模糊半径按性能与背景复杂度调整。
- 行高、侧栏宽度和工具栏尺寸按目标数据密度在规范值域内调整。
- Web/Electron 模拟系统材质；原生 AppKit/SwiftUI 优先使用平台能力。
- 目标产品原有主题数量保持不变；没有暗色时不强加暗色。

## archetype-bound

- hiddenInset 标题栏、内缩侧栏卡、胶囊工具组适合桌面多区域工作区。
- Finder 三视图、Quick Look 和路径编辑只在目标具有同类任务时采用。
- 来源布局不兼容时保留目标区域关系，只迁移材质、密度、状态和控件语言。

## source-specific

- 文件夹、磁盘、标签颜色、红绿灯位置和 Finder 专属菜单结构不是通用风格要求。
- 不把目标导航改成文件层级，不为相似度新增 Quick Look 或三视图。

## 未覆盖组件推导

先确定所在表面，再复用单蓝规则和通用状态矩阵；尺寸取 28/30/32 热区档，分层优先用材质差、发丝边和留白。业务状态使用图标+文字，危险色只在确认阶段出现。

## 还原验收权重

`color 15 / material 20 / typography 10 / geometry 10 / spacing-density 10 / component-states 20 / motion-feedback 10 / layout-motif 5`
