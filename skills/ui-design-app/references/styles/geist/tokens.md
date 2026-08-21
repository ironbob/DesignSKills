# Geist 风格 · Token 总表（v0.x）

> 数值为近似提炼，未经逐像素核对（v0.x）。
> 开发者仪表盘风（完整 Geist design system 中的 Vercel-dashboard monochrome profile）。亮色默认（`[data-theme="light"]`），
> 暗色挂 `:root`。CSS 变量块：`assets/styles/geist/tokens.css`。
> 本 profile 与 linear 的主要差异：**中性骨架 + 黑白反转主按钮 + 等宽字体点缀 + 语义色状态**。
> 完整 Geist 含多组色阶，不能从本 profile 推断“Geist 只有黑白”。密度中等（比 linear 松、比 finder 紧）。

## 1. 语义色

| Token | 亮 | 暗 | 用途 |
| --- | --- | --- | --- |
| `--ge-canvas` | `#ffffff` | `#000000` | 应用底（暗色真黑是 Geist 签名） |
| `--ge-surface` | `#fafafa` | `#0a0a0a` | 次表面（侧栏/表格外框内衬） |
| `--ge-elevated` | `#ffffff` | `#111111` | 浮层（菜单/命令面板/Tooltip），配边框 |
| `--ge-border` | `#eaeaea` | `#262626` | 常规边框（Vercel 标志性浅灰细线） |
| `--ge-border-strong` | `#d4d4d4` | `#333333` | 输入框/hover 边框 |
| `--ge-text` | `#171717` | `#ededed` | 主文字 |
| `--ge-text-secondary` | `#666666` | `#a1a1a1` | 次级文字（页面描述/表头） |
| `--ge-text-tertiary` | `#999999` | `#737373` | 三级（占位/禁用/时间戳） |
| `--ge-accent` | `#0070f3` | `#0070f3` | Vercel 蓝：**仅** 链接/选中文字/焦点/进行中，**不做主按钮** |
| `--ge-accent-hover` | `#3291ff` | `#3291ff` | 链接 hover |
| `--ge-on-accent` | `#ffffff` | `#ffffff` | 蓝色实底上的文字（用量条/链接钮） |
| `--ge-primary-bg` | `#000000` | `#ffffff` | **主按钮底（黑白反转，Geist 身份）** |
| `--ge-primary-fg` | `#ffffff` | `#000000` | 主按钮文字 |
| `--ge-primary-hover` | `#333333` | `#eaeaea` | 主按钮 hover |
| `--ge-hover` | `rgba(0,0,0,.04)` | `rgba(255,255,255,.06)` | 行/钮 hover |
| `--ge-active` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.1)` | 按压 |
| `--ge-selected` | `rgba(0,0,0,.06)` | `rgba(255,255,255,.08)` | 列表选中灰底（配 accent 文字，不反白） |
| `--ge-success` | `#0e9f6e` | `#0e9f6e` | Ready/成功：状态点/pill 文字 |
| `--ge-success-bg` | `rgba(14,159,110,.1)` | `rgba(14,159,110,.15)` | 成功 pill 淡彩底（**允许**，与 linear 相反） |
| `--ge-warning` | `#f5a623` | `#f5a623` | Building/警告 |
| `--ge-warning-bg` | `rgba(245,166,35,.12)` | `rgba(245,166,35,.15)` | 警告 pill 淡彩底 |
| `--ge-danger` | `#ee0000` | `#ee0000` | Error/危险 |
| `--ge-danger-bg` | `rgba(238,0,0,.08)` | `rgba(238,0,0,.15)` | 危险 pill 淡彩底 |
| `--ge-purple` | `#7928ca` | `#7928ca` | 品牌紫（渐变辅助，仅品牌场合，日常 UI 不用） |
| `--ge-shadow-sm` | `0 0 0 1px rgba(0,0,0,.04)` | `0 0 0 1px rgba(0,0,0,.04)` | 卡片描边影（白底卡片的 1px 勾边） |
| `--ge-shadow` | `0 8px 30px rgba(0,0,0,.12)` | `0 8px 30px rgba(0,0,0,.12)` | 浮层阴影（Geist 经典大柔影） |
| `--ge-scrim` | `rgba(0,0,0,.5)` | `rgba(0,0,0,.65)` | 模态遮罩 |

profile 规则：界面骨架以黑白灰为主；蓝用于链接/选中/焦点/进行中；主按钮在本 profile 黑白反转。
状态 pill 可用淡彩底 + 深彩字 + 状态点，但完整 Geist 的语义色也可用于其他合适组件。

## 2. 排版

字体栈：`Geist, Inter, -apple-system, "SF Pro Text", "PingFang SC", sans-serif`
（本包落地用系统回退栈，不引外链字体；真实工程可引 Geist Sans/Mono）。
等宽：`Geist Mono, ui-monospace, "SF Mono", Menlo`——commit hash / 分支名 / ID / 数值
一律 mono，等宽点缀是身份。
平滑：`-webkit-font-smoothing: antialiased`。

| 级 | 值 | 用途 |
| --- | --- | --- |
| 基准 | **14px** / 400 | 正文、表格、按钮（比 linear 的 13 松一档） |
| 次级 | 13px / 400 secondary | 元信息、键值说明 |
| 小字 | 12px / 500 secondary | 标签（可大写 + ls .04em）、表头 |
| 页面标题 | 20px / 600 | 页头标题，下配 14px secondary 描述 |
| mono | 13px mono | 分支/hash/ID/数值（Geist 身份） |

## 3. 几何（中等密度）

| 项 | 值 |
| --- | --- |
| 圆角 | 控件 6 / 卡片 8 / pill 999（**不超 10**） |
| 控件高 | 按钮·输入 32；图标钮 28 |
| 表格行 | 36-40（比 linear 松） |
| 侧栏宽 | 240-260（导航带图标，比 linear 宽） |
| 边框 | 1px 分层；卡片另加 `--ge-shadow-sm` 描边影 |
| 图标 | 16px，stroke 1.5 |

## 4. 动效

- 状态过渡 `120ms ease`（hover/按压）；弹层 `150ms`（opacity + scale(.98)→1）。
- Building 状态点脉冲 `1.6s ease-in-out infinite`（唯一常驻动画）。
- 全部尊重 `prefers-reduced-motion`（脉冲也停）。

## 5. 阴影（三档）

| | 亮 | 暗 |
| --- | --- | --- |
| 卡片 | `--ge-shadow-sm`（1px 勾边） | 同左 |
| 弹层 | `0 4px 8px rgba(0,0,0,.12)` | 同左 |
| 浮层/命令面板 | `0 8px 30px rgba(0,0,0,.12)` | 同左 |

面板之间不用大阴影，靠边框；浮出内容才有大柔影。

## 6. 焦点环

统一 `0 0 0 2px var(--ge-accent)`，仅 `:focus-visible`。输入聚焦 = `border-strong` + 焦点环。
