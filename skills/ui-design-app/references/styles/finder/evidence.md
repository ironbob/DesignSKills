# Finder 风格 · 证据

## 采样范围

- `source-product`: Apple Finder
- `source-version`: macOS Tahoe 26 documentation snapshot
- `platforms`: macOS 26
- `collected-at`: 2026-08-21
- `evidence-grade`: B
- `representation`: Finder-inspired macOS desktop chrome; CSS materials are web/Electron adaptations

## 官方来源

| ID | 官方来源 | 版本/日期 | 支持的结论 |
| --- | --- | --- | --- |
| O-FD-01 | [Use the Finder on Mac](https://support.apple.com/guide/mac-help/organize-your-files-in-the-finder-mchlp2605/mac) | macOS Tahoe 26 页面 | 左侧栏、顶部视图/整理/共享工具、内容视图、Preview pane、排序/分组、标签 |
| O-FD-02 | [Apple HIG: Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars) | 2026-08 采样 | leading sidebar、Liquid Glass 层、分组/折叠、可隐藏、用户 accent color、随窗口收起 |
| O-FD-03 | [Apple HIG: Toolbars](https://developer.apple.com/design/human-interface-guidelines/toolbars) | 2026-08 采样 | 工具栏承担当前视图高频操作；平台工具栏而非网页导航条 |
| O-FD-04 | [Use tags to organize files on Mac](https://support.apple.com/guide/mac-help/use-tags-to-organize-files-mchlp15236/mac) | macOS User Guide | 标签可在工具栏和侧栏出现；彩色标签属于文件组织语义 |

## observed

- `O-FD-01` Finder 的可辨识骨架是 sidebar + toolbar + 可切换内容视图；Preview pane 是可选能力，不是所有 Finder 风格页面的必需区域。
- `O-FD-02` 当前 macOS 侧栏材质属于系统 Liquid Glass/平台材质，并允许用户隐藏或在窄窗下自动收起。
- `O-FD-02` 侧栏图标通常跟随用户 accent color；固定给全部图标着色不符合平台预期。
- `O-FD-01`、`O-FD-04` 文件标签、视图切换、排序/分组是 Finder 功能，不是任意 app 的通用视觉身份。

## derived

- `D-FD-01` 本包的 28/30/32px 控件档、侧栏宽度、发丝边和阴影为跨截图与 macOS 实践归纳，不是 Apple 发布的 Finder 精确 Token。
- `D-FD-02` “系统蓝稀缺使用 + 失活降级 + 中性 hover”的状态矩阵是平台状态语言归纳；具体 alpha 由目标背景校准。
- `D-FD-03` 自绘菜单的三列对齐与蓝底高亮用于接近 macOS 菜单观感，但网页实现不能宣称为 NSMenu 本身。

## adapted

- `A-FD-01` Web/Electron 用 `backdrop-filter`、半透明填充和实色 fallback 模拟系统材质；原生 AppKit/SwiftUI 应改用平台材料。
- `A-FD-02` 小于 24px 的视觉控件扩大命中热区，焦点使用 `:focus-visible`，不复制来源截图中不可见的可访问性缺口。
- `A-FD-03` 目标不是文件浏览器时保留其导航和内容关系，不新增三视图、标签、Quick Look 或路径栏。

## 视觉覆盖

| 默认骨架 | 交互状态 | 浮层 | 异常/边界 | 窄窗 | 主题 |
| --- | --- | --- | --- | --- | --- |
| 官方 Finder 图与指南：有 | 平台指南：部分 | 自绘菜单：derived | 空/错误：缺 | HIG 收起规则：有 | 系统自动外观：有；精确样本缺 |

## 证据缺口与禁止断言

- 官方页面没有公开 Finder 的完整颜色、圆角、阴影、blur 半径和动效 Token；本包所有此类数值均为 derived。
- 系统材质受壁纸、窗口激活、Reduce Transparency、硬件和系统版本影响；单张截图不能定义唯一颜色。
- 不得将当前 CSS 称为“Apple 官方 CSS”“逐像素 Finder”或把文件管理布局强套给其他产品。

## 刷新条件

- macOS 主版本或 HIG 材质模型变化；Finder 工具栏/侧栏重构；Apple 更新 accent、可访问性或窗口行为指导。
