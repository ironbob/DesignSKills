# Figma 风格 · Token 总表（v0.x）

> 专业创作工具 chrome（Figma 桌面端 UI3 观感）。亮色默认（`data-theme="light"`），暗色挂 `:root`/`data-theme="dark"`。
> 身份特征：**白色圆角浮板漂浮在中灰画板上（面板间留 8px 间隙）+ 全目录最微型控件 + 选中蓝画布语义**。
> CSS 变量块：`assets/styles/figma/tokens.css`。
> 数值为近似提炼，未经逐像素核对（v0.x）。

## 1. 语义色

| Token | 亮 | 暗 | 用途 |
| --- | --- | --- | --- |
| `--fig-canvas` | `#b3b3b3` | `#262626` | 画板（工作区底，面板之间的灰色空隙） |
| `--fig-panel` | `#ffffff` | `#2c2c2c` | 浮动面板（工具条/图层/属性），配大柔投影 |
| `--fig-overlay` | `#ffffff` | `#1e1e1e` | 浮层/右键菜单/弹层（暗色比面板深一档） |
| `--fig-border` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.1)` | 面板边框、分隔线 |
| `--fig-border-strong` | `rgba(0,0,0,.16)` | `rgba(255,255,255,.2)` | 输入聚焦边框、手柄边框 |
| `--fig-grid-dot` | `rgba(0,0,0,.15)` | `rgba(255,255,255,.12)` | 画板网格点（1px） |
| `--fig-text` | `#1a1a1a` | `#ffffff` | 主文字 |
| `--fig-text-secondary` | `#6e6e73` | `#999999` | 次级文字（图层名、label） |
| `--fig-text-tertiary` | `#a1a1a6` | `#6e6e6e` | 三级（占位/禁用） |
| `--fig-accent` | `#0d99ff` | `#0d99ff` | **选中蓝**：画布选框/选中图层条/焦点/分享钮 |
| `--fig-accent-hover` | `#3291ff` | `#3291ff` | 强调 hover |
| `--fig-on-accent` | `#ffffff` | `#ffffff` | 强调实底上的文字（尺寸标签/分享钮） |
| `--fig-hover` | `rgba(0,0,0,.05)` | `rgba(255,255,255,.06)` | 行/钮 hover |
| `--fig-active` | `rgba(0,0,0,.1)` | `rgba(255,255,255,.12)` | 按压 |
| `--fig-selected` | `rgba(13,153,255,.12)` | `rgba(13,153,255,.28)` | 图层选中底（+左缘 2px 蓝条） |
| `--fig-component` | `#9f5ffb` | `#9f5ffb` | 组件紫（图层树菱形图标专用，不外溢） |
| `--fig-handle-bg` | `#ffffff` | `#ffffff` | 选框方形手柄底色（亮暗同为白） |
| `--fig-tooltip-bg` | `#1e1e1e` | `#0f0f0f` | Tooltip 底（两主题都是深色浮块） |
| `--fig-on-tooltip` | `#ffffff` | `#ffffff` | Tooltip 文字 |
| `--fig-input-bg` | `#ffffff` | `#1e1e1e` | 数字输入框底（暗色凹进面板） |
| `--fig-scrim` | `rgba(0,0,0,.45)` | `rgba(0,0,0,.65)` | 模态遮罩 |
| `--fig-danger` | `#f24822` | `#f24822` | 危险（删除图层 toast 等），仅小面积 |
| `--fig-success` | `#14ae5c` | `#14ae5c` | 成功状态点/对勾 |

中性纪律：**UI 里无大面积品牌色**——Figma 彩虹只在 logo；蓝色是"画布选中语义"
不是品牌装饰。组件紫只出现在图层树的组件图标上。

## 2. 排版（全目录最小字号档）

字体栈：`Inter, -apple-system, "SF Pro Text", "PingFang SC", sans-serif`；
等宽 `ui-monospace, "SF Mono", Menlo`（HEX 值、数字输入用，配 `font-variant-numeric: tabular-nums`）。

| 级 | 值 | 用途 |
| --- | --- | --- |
| 基准 | **12px** / 400 | 图层名、按钮、菜单行（全目录最小基准） |
| 小字 | 11px / 400-500 | 属性面板值与 label、面板 tab、分组标题（可大写） |
| 数字 | 11px mono tabular | X/Y/W/H、旋转、HEX、不透明度 |
| kbd | 11px mono | 工具单键提示（工具钮 tooltip 内） |

## 3. 几何（最紧凑档）

| 项 | 值 |
| --- | --- |
| 圆角 | 面板 **12**（UI3 大圆角浮板签名）/ 控件 6 / pill·色板 999 |
| 控件高 | 图标钮 24 / 按钮·数字输入 24-28 |
| 图层行 | 28；面板宽 240-260；数字输入宽 56-72 |
| 图标 | 14-16px，stroke 1.5 |
| 面板间隙 | **8px**（浮板之间的画板灰缝，UI3 签名） |

## 4. 动效

状态过渡 `100ms ease`；弹层/菜单 `120ms`（opacity + translateY(4px)）；
选中框显隐 `80ms`。全部尊重 `prefers-reduced-motion`。

## 5. 阴影（面板的身份：大而柔，"物"浮在画板上）

| | 亮 | 暗 |
| --- | --- | --- |
| 面板 | `0 12px 32px rgba(0,0,0,.12), 0 2px 8px rgba(0,0,0,.06)` | `0 12px 32px rgba(0,0,0,.5), 0 2px 8px rgba(0,0,0,.35)` |
| 浮层小投影 | `0 4px 12px rgba(0,0,0,.18), 0 1px 3px rgba(0,0,0,.1)` | `0 4px 12px rgba(0,0,0,.55), 0 1px 3px rgba(0,0,0,.4)` |

无 backdrop blur——浮板是实色"物"，靠投影分层，不是毛玻璃。

## 6. 焦点环

统一 `0 0 0 2px color-mix(in srgb, var(--fig-accent) 45%, transparent)`，
仅 `:focus-visible`；输入聚焦 = `border-strong` + 焦点环。
