# Finder 风格 · Token 总表

> 暗色为默认（`:root`），亮色挂 `[data-theme="light"]`；同时设置 `color-scheme`。
> 可直接使用的 CSS 变量块见 `assets/styles/finder/tokens.css`（数值与本表一致）。

## 1. 语义色（双主题）

| Token | 亮 | 暗 | 用途 |
| --- | --- | --- | --- |
| `--finder-canvas` | `#ffffff` | `#1e1e20` | 主内容画布（文件列表/预览区底色） |
| `--finder-chrome` | `rgba(255,255,255,.76)` | `rgba(40,40,42,.92)` | 标题栏/工具栏/状态栏等 chrome 条 |
| `--finder-label` | `#1d1d1f` | `#f5f5f7` | 主文字 |
| `--finder-secondary-label` | `#6e6e73` | `#a1a1a6` | 次级文字（元数据/状态/快捷键） |
| `--finder-header-label` | `rgba(0,0,0,.62)` | `rgba(255,255,255,.62)` | 列头/分组标题（小字号 semibold 下仍可读） |
| `--finder-nav-icon` | `rgba(60,60,67,.78)` | `rgba(235,235,245,.72)` | 导航图标（稳定深灰；彩色只给标签点/状态） |
| `--finder-divider` | `rgba(60,60,67,.12)` | `rgba(255,255,255,.12)` | 发丝分隔线 |
| `--finder-selection` | `#007aff` | `#0a84ff` | **系统蓝**：选中/高亮/主按钮/焦点环/进行中 |
| `--finder-control` | `rgba(118,118,128,.10)` | `rgba(118,118,128,.28)` | 控件填充底（输入框/开关轨/分段托盘） |
| `--finder-control-strong` | `rgba(118,118,128,.16)` | `rgba(118,118,128,.38)` | 控件 hover 加重底 / quiet-active 开启态 |
| `--finder-zebra` | `rgba(118,118,128,.045)` | `rgba(118,118,128,.06)` | 列表斑马纹（偶数行） |
| `--finder-row-hover` | `rgba(118,118,128,.09)` | `rgba(118,118,128,.13)` | 行 hover（不与选中争级） |
| `--finder-selection-bg` | `rgba(0,0,0,.09)` | `rgba(255,255,255,.18)` | 选中项的**图标底**（浅灰圆角，非蓝） |
| `--finder-selection-text-bg` | `var(--finder-selection)` | 同左 | 选中项的**文字底**（系统蓝） |
| `--finder-selection-text` | `#ffffff` | `#ffffff` | 选中文字色 |
| `--finder-mark-bg` | `rgba(0,0,0,.14)` | `rgba(255,255,255,.35)` | typeahead 命中字符（蓝底上仍可分辨） |
| `--finder-sidebar-inactive-sel` | `#e5e5e7` | `rgba(255,255,255,.12)` | **窗口失焦**时的选中底（灰底蓝字） |
| 失焦蓝字（暗色专用值） | — | `#7cb4ff` | 暗色失焦时文字/图标蓝（深灰底上可读） |

功能色（红橙黄绿，同时用于状态与危险动作）：

| Token | 亮 | 暗 |
| --- | --- | --- |
| red | `#ff3b30` | `#ff4d4d` |
| orange | `#ff9500` | `#ffaa33` |
| yellow | `#ffcc00` | `#ffd60a` |
| green | `#34c759` | `#32d74b` |

材质类 Token（sidebar / capsule / popover / quicklook / menu 家族）见 `materials.md`，不在此重复。

## 2. 排版分级

字体栈：`-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", "PingFang SC", "Helvetica Neue", sans-serif`
等宽栈：`ui-monospace, "SF Mono", SFMono-Regular, Menlo, monospace`

**字体平滑策略**：正文 `-webkit-font-smoothing: auto`（antialiased 会把字形描细，macOS
原生是 subpixel/auto）；仅图标/符号字体用 `antialiased`。

| 级 | 字号/字重 | 颜色 | 用途 |
| --- | --- | --- | --- |
| 基准 | 14px / 400 | label | 正文、Sheet 标题（标题 600） |
| 主行 | **13px / 500** | label（选中白） | 文件名、导航项、菜单行、pill 按钮 |
| 次级 | 12px / 400 | secondary | 元数据列、状态栏、状态条、快捷键 |
| 分组标题 | 12px / 600 / ls .01em | header-label | 侧边栏分组、区域标题 |
| 子分组 | 11px / 600 / ls .01em | header-label | 更次级分组 |
| 列头 | 11px / 500 | header-label | 列表列头、微型标题 |
| 微标题 | 10px / 600 / 大写 / ls .05em | secondary | Inspector 分组等 uppercase caption |
| 徽标 | 9px / 600 | 白 | 数字徽标 |
| kbd 内嵌提示 | 10px / 400 / 75% 透明 | 白（随文字） | 按钮内 ⌘S 提示 |

## 3. 几何

**热区三档**：常规 28×28 / 工具栏圆钮 30 / 关键编辑区 32。最小图标点击热区 28。

| 圆角 | 值 | 用于 |
| --- | --- | --- |
| 微 | 2px | 字符级高亮（find match） |
| 控件 | 5-7px | 图标钮 5、分段钮 6、主/次按钮 7、utility 钮 7 |
| 浮层 | 9-12px | 小浮出工具条 9、Popover/菜单/Sheet 10-12 |
| 卡片 | 14px | 侧边栏浮层卡片 |
| 胶囊 | 18px（=36px 高全圆端）/ 999px | 工具栏胶囊托盘、pill 按钮 |

| 行/条 | 高 |
| --- | --- |
| 标题栏（含内嵌标签栏） | 48px（tab strip 部分 44） |
| 内容工具栏（胶囊模型） | min 56px（padding 10px 14px） |
| 预览/编辑器工具栏 | 40-44px |
| 列表列头 | 25px |
| 列表行 / 菜单行 | 13px 字号，行高约 28（菜单固定 28） |
| 侧边栏条目 | min 30px（margin 1px 8px，padding 4px 10px） |
| 状态栏 | min 24px |
| 过滤状态条 | 28px |

## 4. 动效

| 场景 | 值 |
| --- | --- |
| 控件状态过渡（默认档） | `130ms ease`（背景/颜色/阴影） |
| 分段钮/分割器 | `140ms ease` |
| pill/主按钮 | `150ms ease` |
| 菜单弹出 | `0.09s`：`scale(0.97) translateY(-2px)` → 原位淡入 |
| 媒体控件淡入淡出 | `200ms` |
| 定位脉冲 | `0.4s ease-in-out ×2`（reduced-motion 降级为静态描边） |
| hover 缩放/位移动画 | **禁止**（Finder 图标静态） |

所有动效必须响应 `prefers-reduced-motion: reduce`（时长归零、动画降级为静态）。

## 5. 阴影（双影为主，禁止硬投影/发光）

| 表面 | 亮 | 暗 |
| --- | --- | --- |
| 侧边卡片 | `0 4px 18px rgba(0,0,0,.14)` | `0 4px 18px rgba(0,0,0,.42)` |
| 工具栏胶囊 | `0 3px 12px rgba(0,0,0,.10)` | `0 3px 12px rgba(0,0,0,.32)` |
| Popover | `0 8px 24px rgba(0,0,0,.16)` | `0 10px 28px rgba(0,0,0,.45)` |
| QuickLook 窗 | `0 10px 30px rgba(0,0,0,.18)` | `0 12px 32px rgba(0,0,0,.5)` |
| 菜单 | `0 12px 32px rgba(0,0,0,.18), 0 2px 8px rgba(0,0,0,.10)` | `0 14px 36px rgba(0,0,0,.5), 0 3px 10px rgba(0,0,0,.32)` |
| 激活标签 | `0 1px 2px rgba(0,0,0,.06)` | `0 1px 2px rgba(0,0,0,.35)` |

## 6. 层级（z-index）

```text
base 0 < sidebar 10 < dropdown 20 < sticky 30 < overlay 40 < modal 50 < toast 100
```

例外：标题栏因 backdrop-filter 形成层叠上下文，固定 `z-index: 30` 压过 main，
低于 overlay/modal（详见 patterns.md 窗口解剖）。

## 7. 滚动条

12px 轨道、thumb 全圆角（999px）：静止透明度 0.24、hover 0.50；轨道透明、无箭头；
thumb 带 1px 透明边（`background-clip: padding-box`）留呼吸。自绘 `::-webkit-scrollbar` 实现。
