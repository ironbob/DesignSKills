# Codex 风格 · Token 总表（v0.x）

> 从 Codex 桌面端截图提炼。亮色是截图的默认观感；为遵守本技能的 CSS 契约，`:root` 放暗色，`[data-theme="light"]` 显式覆写亮色。暗色不是截图证据，提供保守等价主题以满足产品双主题实现。可复制变量见 `assets/styles/codex/tokens.css`。

## 章节索引

- §1 语义色；§2 排版；§3 几何；§4 动效；§5 阴影与层级

## 1. 语义色（双主题）

| Token | 亮 | 暗 | 用途 |
| --- | --- | --- | --- |
| `--cx-canvas` | `#ffffff` | `#171717` | 主任务画布 |
| `--cx-sidebar` | `#f8f8f7` | `#20201f` | 左导航区 |
| `--cx-surface` | `#ffffff` | `#272726` | 输入台、检查器、菜单 |
| `--cx-surface-subtle` | `#f5f5f4` | `#2f2f2d` | 次级条、附件区 |
| `--cx-text` | `#202124` | `#f3f3f1` | 主文字 |
| `--cx-text-secondary` | `#6f7175` | `#acaca8` | 元数据、次说明 |
| `--cx-text-tertiary` | `#9b9c9e` | `#7d7e7d` | 占位、弱辅助信息 |
| `--cx-border` | `rgba(32,33,36,.09)` | `rgba(255,255,255,.11)` | 低对比分区线 |
| `--cx-border-strong` | `rgba(32,33,36,.16)` | `rgba(255,255,255,.20)` | 输入/浮卡边界 |
| `--cx-hover` | `rgba(32,33,36,.055)` | `rgba(255,255,255,.08)` | 行与图标 hover |
| `--cx-active` | `rgba(32,33,36,.10)` | `rgba(255,255,255,.14)` | 按压态 |
| `--cx-selected` | `rgba(32,33,36,.075)` | `rgba(255,255,255,.12)` | 项目/会话选中底（不反白） |
| `--cx-accent` | `#2997ff` | `#4ba9ff` | 链接、未读点、焦点环 |
| `--cx-submit` | `#202124` | `#f1f1ee` | 提交按钮；不是全局品牌色 |
| `--cx-on-submit` | `#ffffff` | `#1c1c1b` | 提交按钮文字/图标 |
| `--cx-success` | `#18a957` | `#35c76e` | 正向变更 |
| `--cx-danger` | `#e45555` | `#ff7676` | 风险/失败变更 |

## 2. 排版

字体栈：`-apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Helvetica Neue", sans-serif`。正文务必优先可读性而不是代码编辑器等宽感；只在路径、代码块与快捷键中使用 `ui-monospace`。

| 层级 | 规格 | 用途 |
| --- | --- | --- |
| 侧栏/行 | 13px / 500 | 项目、会话、环境项 |
| 正文 | 14px / 400 / 1.65 | 任务讨论、说明文本 |
| 页面标题 | 14px / 600 | 顶部当前任务 |
| 区域标题 | 12px / 600 | 检查器分组、侧栏分组 |
| 辅助文字 | 12px / 400 | 分组标签、来源、时间 |
| 输入 | 14px / 400 | composer 与搜索 |

## 3. 几何

| 部件 | 规格 |
| --- | --- |
| 左侧栏 | 270px；可在 240–320px 间拖拽 |
| 右检查器 | 272px；`max-width: calc(100vw - 80px)` |
| 顶栏 | 48px；与内容用发丝线分隔 |
| 侧栏行 | min 28px；水平内边距 10px；圆角 8px |
| 主内容列 | `min(672px, calc(100% - 48px))`；避免满宽长行 |
| 浮卡/输入台 | r 16px；边缘柔和且阴影克制 |
| 项目菜单 | 520px 宽；r 24px；行高 56px |
| 常规图标热区 | 28×28；提交按钮 28×28 圆形 |

## 4. 动效

`120ms ease-out` 用于 hover、选中和检查器展开；`160ms cubic-bezier(.2,.8,.2,1)` 用于菜单与输入台进入。禁止悬停缩放、弹跳、渐变扫光。所有动效响应 `prefers-reduced-motion`。

## 5. 阴影与层级

亮：浮卡 `0 5px 18px rgba(0,0,0,.07), 0 1px 3px rgba(0,0,0,.04)`；菜单 `0 18px 42px rgba(0,0,0,.14)`。暗色阴影加深约 2 倍。层级：base 0 < sticky topbar 20 < inspector 30 < menu 40 < modal 50。
