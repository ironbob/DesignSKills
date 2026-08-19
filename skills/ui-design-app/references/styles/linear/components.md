# Linear 风格 · 控件规格库（v0.x）

> 实现见 `assets/styles/linear/linear-ui.css`（`.ln-shell` 作用域）。

## 1. 状态语义（全控件）

| 状态 | 值 |
| --- | --- |
| 默认 | 透明底 + secondary 图标/文字 |
| hover | `ln-hover` 浅底 + 边框加深（输入类） |
| 按压 | `ln-active` |
| 主操作 | `accent` 实底白字（每屏至多 1 个） |
| 选中（列表） | `ln-selected` 弱紫底 + 主文字保持（**不反白**） |
| 禁用 | opacity .45 + not-allowed |
| 焦点 | 2px 45% 紫环，仅 :focus-visible |

过渡 100ms ease。

## 2. 控件清单

### 按钮

| 类 | 规格 |
| --- | --- |
| 主按钮 | 高 28、r6、紫底白字 13px/500；hover `accent-hover` |
| 次按钮 | 高 28、r6、透明底 + 1px `border`、主文字色；hover 灰底 |
| ghost 钮 | 同次按钮无边框；工具栏动作用 |
| 图标钮 | 24×24（紧凑 22）、r4、16px 图标 |
| 带快捷键的按钮 | 右侧内嵌 kbd chip（11px mono + 边框）——Linear 身份特征 |

### 输入

| 控件 | 规格 |
| --- | --- |
| 输入框 | 高 28、r6、L0 底 + 1px `border`；聚焦 border-strong + 2px 45% 紫环；占位 tertiary |
| 搜索/过滤框 | 同上 + 左放大镜 + 右清除；输入即过滤（无确定钮） |
| 下拉选择 | 输入框样式 + 右 chevron；菜单 = 浮层配方，行 28、hover 灰底、选中项紫对勾 |

### 列表（主体 UI）

- 行高 28-32、r4 hover 灰底、选中弱紫底；行内：状态图标（色点/勾 14px）+ 主文字 13px +
  次信息 12px tertiary 右对齐 + 头像圆 18px。
- 分组头：11px/500 tertiary 大写可选（ls .04em）。
- 密度是风格核心：不留大于 8px 的行内空隙。

### 键盘提示（kbd chip）

```css
font: 500 11px/1 ui-monospace, Menlo, monospace;
padding: 2px 5px; border: 1px solid var(--ln-border-strong); border-radius: 4px;
color: var(--ln-text-secondary); background: var(--ln-canvas);
```

用于：按钮内、命令面板行尾、快捷键列表、hover Tooltip。

### 菜单/命令面板

- 浮层配方（materials.md）；行 28px、r4、hover `ln-hover`（灰，非蓝）。
- 快捷键右对齐 tertiary；分组用 11px tertiary 标题 + 上 6px 间距。
- 命令面板：居中偏上（top 20%）、宽 560-640、输入无框融合进浮层头部、
  出现 80ms；空态给可用命令提示。

### 徽标/标签

- 计数：18px 高、r4、`ln-hover` 底、11px/500 secondary。
- 彩色标签：**只作为小圆点或 11px 文字+圆点**，不做彩色底胶囊。

## 3. 反模式（linear 专属）

1. 大圆角（>8）、胶囊按钮——那是 finder/消费风。
2. backdrop blur / 半透明面板。
3. 多彩图标导航；彩色底标签。
4. 蓝色系高亮（高亮一律灰底；紫只给主操作与选中）。
5. 宽松行距、大标题 chrome、大面积留白。
6. 无快捷键的按钮（键盘优先风格里每个高频动作都该有 ⌘ 键）。
