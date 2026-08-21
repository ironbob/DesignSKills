# Geist 风格 · 控件规格库（v0.x）

> 实现见 `assets/styles/geist/geist-ui.css`（`.ge-shell` 作用域）。
> 数值为近似提炼（v0.x）。

## 1. 状态语义（全控件）

| 状态 | 值 |
| --- | --- |
| 默认 | 透明底 + secondary 图标/文字 |
| hover | `ge-hover` 浅灰底 + 边框加深（输入类） |
| 按压 | `ge-active` |
| 主操作 | `primary-bg` 黑底 `primary-fg` 白字（暗色反转白底黑字），每屏至多 1-2 个 |
| 选中（导航/菜单） | `ge-selected` 灰底 + **accent 文字**（不反白、不蓝底） |
| 禁用 | opacity .45 + not-allowed |
| 焦点 | 2px `--ge-accent` 蓝环，仅 :focus-visible |

过渡 120ms ease。

## 2. 控件清单

### 按钮

| 类 | 规格 |
| --- | --- |
| 主按钮 `.ge-btn.primary` | 高 32、r6、**黑底白字** 14px/500；hover `primary-hover`（#333） |
| 次按钮 `.ge-btn.secondary` | 高 32、r6、L0 底 + 1px `border`、主文字色；hover 灰底+边框加深 |
| ghost 钮 | 无边框透明底，hover 灰底；工具栏用 |
| 图标钮 | 28×28、r6、16px 图标 |
| 危险钮 | 文字 `--ge-danger`，实底红只出现在二次确认 |

在本 monochrome profile 中主按钮不使用蓝——蓝属于链接/选中/焦点；其他 Geist profile 需另行声明。

### 输入 / 开关

| 控件 | 规格 |
| --- | --- |
| 输入框 | 高 32、r6、surface 底 + 1px `border`；聚焦 border-strong + 2px 蓝环；占位 tertiary |
| 下拉选择 | 输入框样式 + 右 chevron；菜单 = 浮层配方，行 32、hover 灰底 |
| 开关（switch） | 轨 32×16、r999、关闭 = surface 底+边框；开启 = `--ge-accent` 蓝轨白点 |

### 表格（部署列表，主体 UI）

- 行高 36-40、列间 16px、表头 12px/500 secondary 大写可选；
- 行内容从左到右：状态 pill + 提交信息（主文字）+ 分支名（**mono** 13px）+ 相对时间（tertiary 右对齐）；
- 行 hover = `--ge-hover` 灰底；行间 1px `border` 分隔。

### 状态 pill

```css
display: inline-flex; align-items: center; gap: 6px;
height: 22px; padding: 0 9px; border-radius: 999px;
background: var(--ge-success-bg); color: var(--ge-success);
```

配 6px 圆点：Ready 绿 / Building 黄 + 脉冲 / Error 红 / Canceled 灰（muted）。
本 profile 允许淡彩底；完整 Geist 的语义色也可用于其他合适组件，不应误写成“颜色只能用于 pill”。

### 键值设置行（账户设置页模式，Geist 身份组件）

`.ge-kv`：label 左（14px 主文字 + 13px secondary 描述）、控件右（switch/输入/按钮），
行高约 48-56，行间 1px 边框，整卡 r8 + 描边影。

### 用量条形图 / 进度条

`.ge-meters`：6-12 根竖条，高按值 20%-100%，条色 `--ge-accent`（超限灰/红），
条 r2、间距 4px，配 mono 数值标签。CSS 实现，无图表库。

### 键盘提示（kbd）

```css
font: 500 11px/1 Geist Mono, ui-monospace, Menlo, monospace;
padding: 2px 5px; border: 1px solid var(--ge-border-strong); border-radius: 4px;
```

比 linear 克制：只在 ⌘K 命令菜单和快捷键列表出现，不塞进每个按钮。

### ⌘K 命令菜单 / toast

- 命令菜单：居中偏上（top 15%）、宽 560-640、输入融合进浮层头部、150ms 出现、Esc 关闭。
- toast：右下角、r8、elevated 底 + 描边影、3s 自动消失。

## 3. 反模式（geist 专属）

1. 在未声明新 profile 时把主按钮改蓝；本 profile 的主钮使用黑白反转。
2. 彩色渐变大色块、品牌紫出现在日常 UI（紫仅品牌场合）。
3. 暖灰（#faf9f7 系）——灰阶必须中性。
4. 大圆角 >10、胶囊按钮（pill 999 只属于状态 pill，不属按钮）。
5. backdrop blur / 半透明面板。
6. 等宽滥用——mono 只给 分支/hash/ID/数值，不给正文。
