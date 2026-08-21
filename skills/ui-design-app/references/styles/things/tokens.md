# Things 风格 · Token 总表（v0.x）

> 仿 Cultured Code Things 3（Apple Design Award 获奖任务管理 app）：「有产品个性的清爽」。
> **亮色为人设默认**（`:root` 为暗色块，demo 挂 `data-theme="light"`）。
> 默认 `classic-solid` 与 finder 的差异：实色白净 + 大留白 + 大标题 + 宽松行距；Things 3.22/OS 26 可选 `os26-glass` 只在侧栏/小控件加入克制材质，见 `evidence.md`；
> 与 linear 的差异：密度全目录最松、动效舒缓、单蓝强调不反白高亮。
> CSS 变量块：`assets/styles/things/tokens.css`。
> 数值为近似提炼，未经逐像素核对（v0.x）。

## 0. 材质 profile

- `data-material="classic-solid"`：默认离线样张；侧栏和控件实色，不使用 blur/scale。
- `data-material="os26-glass"`：Things 3.22/OS 26 适配；复用同一语义色，只在 sidebar/chrome 增加 derived 的 `blur(22px) saturate(1.18)` 与实色 fallback，小按钮 hover 最多 `scale(1.015)`。
- 上述 blur/scale 是保守 adapted 值，不是 Cultured Code 官方 Token；目标平台 Reduce Transparency 或 reduced motion 时必须降级。

## 1. 语义色

| Token | 亮 | 暗 | 用途 |
| --- | --- | --- | --- |
| `--th-canvas` | `#ffffff` | `#2b2b2e` | 内容画布（白净是身份） |
| `--th-sidebar` | `#f4f4f6` | `#212123` | 侧栏面板 |
| `--th-elevated` | `#ffffff` | `#323236` | 二级浮层（快捷查找/日期选择器） |
| `--th-border` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.10)` | 常规边框 |
| `--th-border-strong` | `rgba(0,0,0,.14)` | `rgba(255,255,255,.16)` | 输入框/hover 边框 |
| `--th-text` | `#1d1d1f` | `#f2f2f4` | 主文字（近黑，非纯黑） |
| `--th-text-secondary` | `#8a8a8e` | `#9a9aa0` | 次级文字/分组头 |
| `--th-text-tertiary` | `#b0b0b5` | `#77777d` | 占位/禁用 |
| `--th-accent` | `#3f8fe8` | `#4a94e8` | **唯一强调色** Things 蓝：复选框/今日/主按钮/焦点 |
| `--th-accent-hover` | `#5299ec` | `#5ba0f0` | 强调 hover |
| `--th-on-accent` | `#ffffff` | `#ffffff` | 强调实底上的勾/文字 |
| `--th-hover` | `rgba(0,0,0,.04)` | `rgba(255,255,255,.05)` | 行/钮 hover |
| `--th-active` | `rgba(0,0,0,.08)` | `rgba(255,255,255,.09)` | 按压 |
| `--th-selected` | `rgba(63,143,232,.12)` | `rgba(74,148,232,.22)` | 列表选中弱蓝底（**不反白**） |
| `--th-done` | `#8a8a8e` | `#77777d` | 已完成事项的划线灰 |
| `--th-tag-bg` | `rgba(0,0,0,.05)` | `rgba(255,255,255,.08)` | 标签胶囊/日期 pill 底 |

单强调色规则：蓝只给 复选框完成态 / 今日 pill / 主按钮（每屏至多 1 个）/ 焦点环 / 侧栏图标；
选中一律弱蓝底不反白（与 finder 的蓝实底反白相反）。

## 2. 区域色板（Things 身份：区域/清单彩色圆点，亮暗同值）

| Token | 亮 | 暗 | 用途 |
| --- | --- | --- | --- |
| `--th-area-blue` | `#3f8fe8` | 同左 | 区域点·蓝（默认「工作」） |
| `--th-area-green` | `#40ad54` | 同左 | 区域点·绿（家庭） |
| `--th-area-orange` | `#f29441` | 同左 | 区域点·橙 |
| `--th-area-red` | `#e25f5c` | 同左 | 区域点·红（也是 danger，仅小面积） |
| `--th-area-purple` | `#8e6fc0` | 同左 | 区域点·紫 |
| `--th-area-teal` | `#3aa9a2` | 同左 | 区域点·青 |
| `--th-area-pink` | `#d76bb0` | 同左 | 区域点·粉 |

区域色**只出现在 10px 正圆点**上，不做彩色底、彩色文字、彩色图标。

## 3. 排版

字体栈：`-apple-system, "SF Pro Text", "PingFang SC", sans-serif`（系统栈，不引外部字体）。
平滑：`-webkit-font-smoothing: antialiased`。

| 级 | 值 | 用途 |
| --- | --- | --- |
| 基准 | **14px** / 400 | 正文、todo 行（比 linear 的 13 大一号） |
| 次级 | 13px / 600 secondary | 分组头（「今晚」「收件箱」） |
| 小字 | 12px / 400 secondary | 日期 pill、标签、计数 |
| 页面大标题 | **22px / 600** | 「今天」「收件箱」——大标题是身份特征 |
| kbd | 11px mono chip | 快捷键提示，默认隐藏、hover 才浮现 |

## 4. 几何（宽松档，全目录最松）

| 项 | 值 |
| --- | --- |
| 圆角 | 控件 6 / 卡片·浮层 10 / 复选框·区域点**正圆** |
| todo 行高 | **40-44**（demo 用 min-height 42） |
| 控件高 | 按钮 32 / 图标钮 28 / 输入·新建行 36 |
| 侧栏宽 | 220-240（demo 232）；无图标栏（单栏侧栏） |
| 内容留白 | 左右 36、分组间 18+、行内 gap 12 |
| 边框 | 面板间 1px 边框，**不用阴影** |
| 图标 | 16-18px，stroke 1.5 |

OS 26 profile 可把可按压小控件圆角从 6 提到约 9；内容容器和 todo 行不因此胶囊化。

## 5. 动效（舒缓是身份）

- 状态过渡 `150ms ease`（linear 是 100ms，finder 即时）。
- 完成**勾选 250ms**：蓝底填充 + 白勾缩放 + 文字划线灰化同步。
- 浮层 `180ms` 上浮出现（translateY(6px)→0）。
- 全部尊重 `prefers-reduced-motion`。

## 6. 阴影（只有浮层用）

| | 亮 | 暗 |
| --- | --- | --- |
| 浮层 | `0 8px 24px rgba(0,0,0,.10), 0 1px 3px rgba(0,0,0,.06)` | `0 8px 24px rgba(0,0,0,.50), 0 1px 3px rgba(0,0,0,.35)` |
| 遮罩 | `rgba(0,0,0,.35)` | `rgba(0,0,0,.50)` |

面板之间不用阴影；Things 的柔和大投影只属于快捷查找/日期选择器等浮出内容。

## 7. 焦点环

统一 `0 0 0 2px` 当量的 `outline: 2px solid color-mix(in srgb, var(--th-accent) 50%, transparent)`，
仅 `:focus-visible`。
