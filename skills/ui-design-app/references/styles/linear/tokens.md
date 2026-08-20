# Linear 风格 · Token 总表（v0.x）

> 现代 SaaS 效率风（Linear/Notion 一脉）。暗色默认（`:root`），亮色挂 `[data-theme="light"]`。
> 与 finder 的根本差异：**实色分层（无 backdrop blur）+ 单一品牌强调色 + 紧凑密度 + 快动效**。
> CSS 变量块：`assets/styles/linear/tokens.css`。

## 1. 语义色

| Token | 亮 | 暗 | 用途 |
| --- | --- | --- | --- |
| `--ln-canvas` | `#ffffff` | `#08090a` | 应用底 |
| `--ln-surface` | `#f9f9fa` | `#0f1011` | 一级面板（侧栏/列表列） |
| `--ln-elevated` | `#ffffff` | `#16181d` | 二级浮层（菜单/弹层/命令面板），配边框 |
| `--ln-border` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.07)` | 常规边框 |
| `--ln-border-strong` | `rgba(0,0,0,.14)` | `rgba(255,255,255,.12)` | 输入框/hover 边框 |
| `--ln-text` | `#16171a` | `#f7f8f8` | 主文字 |
| `--ln-text-secondary` | `#6b6f76` | `#8a8f98` | 次级文字 |
| `--ln-text-tertiary` | `#6f737a` | `#767b84` | 三级（占位/禁用文字，常规小字保持可读对比度） |
| `--ln-accent` | `#5e6ad2` | `#5e6ad2` | **唯一强调色**（品牌紫）：主按钮/选中/链接/焦点 |
| `--ln-accent-hover` | `#6874e0` | `#6874e0` | 强调 hover |
| `--ln-on-accent` | `#ffffff` | `#ffffff` | 强调色实底上的文字与图标 |
| `--ln-hover` | `rgba(0,0,0,.04)` | `rgba(255,255,255,.05)` | 行/钮 hover |
| `--ln-active` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.09)` | 按压 |
| `--ln-selected` | `rgba(94,106,210,.10)` | `rgba(94,106,210,.22)` | 列表选中底（弱化，非实心） |
| 状态色 | success `#4cb782` / danger `#eb5757` / warning `#f2994a` | 同亮 | 只用于小图标/文字/边点，**不做大面积底色** |

单强调色规则：紫只给 主按钮 / 当前选中 / 链接 / 焦点环 / 进行中；红色只给危险确认，
不常驻。状态一律"小图标+文字"，不做彩色底大块。

## 2. 排版

字体栈：`Inter, -apple-system, "SF Pro Text", "PingFang SC", sans-serif`（Inter 优先；
等宽 `ui-monospace, "SF Mono", Menlo`）。
平滑：`-webkit-font-smoothing: antialiased`（Web 产品字体用 antialiased 显精致，
与 finder 的 auto 策略相反——这是刻意的风格差异）。

| 级 | 值 | 用途 |
| --- | --- | --- |
| 基准 | **13px** / 400 | 正文、列表行、按钮（比 finder 的 14 更紧） |
| 次级 | 12px / 400 secondary | 元信息、面包屑、快捷键 |
| 小字 | 11px / 500 tertiary | 微标签、计数 |
| 标题 | 14-16px / 600 | 页面/弹层标题 |
| kbd | 11px mono / 边框 chip | 快捷键提示（Linear 的身份特征，随处可见） |

## 3. 几何（紧凑档）

| 项 | 值 |
| --- | --- |
| 圆角 | 微 4 / 控件 6 / 面板·弹层 8（**无 12+ 大圆角、无胶囊**） |
| 控件高 | 图标钮 24 / 按钮·输入 28（紧凑档 26） |
| 列表行 | 28-32（finder 是 30-36） |
| 侧栏宽 | 220-240；图标栏 48 |
| 边框 | 分层靠 1px 边框 + 表面色差，**不靠阴影** |
| 图标 | 16px，stroke 1.5-1.8 |

## 4. 动效

- 状态过渡 `100ms ease`（hover/按压）；弹层 `120ms`（opacity + translateY(4px)）。
- 命令面板 `80ms` 出现——键盘流里弹层必须"瞬时"。
- 全部尊重 `prefers-reduced-motion`。

## 5. 阴影（克制，仅浮层用）

| | 亮 | 暗 |
| --- | --- | --- |
| 浮层 | `0 4px 12px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06)` | `0 4px 16px rgba(0,0,0,.45), 0 1px 2px rgba(0,0,0,.3)` |

面板之间**不用阴影**，用边框；只有浮出内容（菜单/弹层/命令面板）才有阴影。

## 6. 焦点环

统一 `0 0 0 2px color-mix(in srgb, var(--ln-accent) 45%, transparent)`，
仅 `:focus-visible`。输入聚焦 = `border-strong` + 焦点环。
