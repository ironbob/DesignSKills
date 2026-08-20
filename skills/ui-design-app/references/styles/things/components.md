# Things 风格 · 控件规格库（v0.x）

> 实现见 `assets/styles/things/things-ui.css`（`.th-shell` 作用域）。

## 1. 状态语义（全控件）

| 状态 | 值 |
| --- | --- |
| 默认 | 透明底 |
| hover | `th-hover` 极浅底（.04） |
| 按压 | `th-active`（.08） |
| 主操作 | `accent` 蓝底白字，每屏至多 1 个 |
| 选中（侧栏/行） | `th-selected` 弱蓝底 + 主文字保持（**不反白**） |
| 完成 | 复选框蓝底白勾 + 标题 `th-done` 划线灰化 |
| 禁用 | opacity .45 + not-allowed |
| 焦点 | 2px 50% 蓝环，仅 :focus-visible |

过渡 150ms ease（勾选动画 250ms）。

## 2. 控件清单

### 圆形复选框（灵魂控件）

```css
20×20、border 1.5px tertiary、border-radius: 50%（正圆）；
hover 边框转 accent；完成 = 蓝底白勾，250ms 填充 + 勾缩放出现；
同行标题同步划线灰化。button role="switch" aria-checked 驱动。
```

### todo 行（宽松档核心）

- min-height 42、r6、行内 gap 12：复选框 + 标题 14px + 右侧日期 pill/标签。
- hover 浅底、按压 active；无选中反白。
- 新建行 `.th-new`：顶部内联，22px 圆形蓝底加号 + 占位文本「新增事项」，⌘N 聚焦。

### 日期 pill（`.th-when`）

高 24、r6、`th-tag-bg` 底、12px；内嵌小日历图标 + 「今晚 8:00」「明天」；
**今天/今晚用 accent 蓝字**，其余 secondary。

### 标签胶囊（`.th-tag`）

高 22、**胶囊圆角 999**（Things 少数的胶囊形态）、灰底 12px + 7px 区域色点；
不做彩色底标签。

### 按钮

| 类 | 规格 |
| --- | --- |
| 主按钮 | 高 32、r6、蓝底白字 14px/500；hover `accent-hover` |
| 次按钮 | 高 32、透明底 + 1px `border-strong`；hover 灰底 |
| ghost/图标钮 | 28×28、r6、secondary 图标 |
| 快捷键提示 | kbd chip **默认隐藏，hover 才浮现**（克制） |

### 菜单 / 快捷查找（⌘F）

- 浮层配方（materials.md）；r10、行 min-height 32、hover 灰底。
- 快捷查找：居中偏上、宽 480、180ms 上浮；输入无框融合进浮层头部；Esc 关闭。
- macOS 实色右键菜单同配方：灰底 hover，不用蓝底反白。

### 侧栏

- 单栏（无图标栏）：nav 行高 34、r6、图标 **17px accent 蓝**（智能列表）或 10px 区域色点；
  active = `th-selected` 弱蓝底；计数右对齐 12px secondary。

## 3. 反模式（things 专属）

1. 紧凑密度（行 <40、控件 <28）——宽松是身份，linear 才紧。
2. 蓝底反白高亮（选中/菜单一律弱蓝或灰底）。
3. backdrop blur / 毛玻璃 / 半透明面板（那是 finder）。
4. 大紫大绿品牌色堆叠——单蓝是身份，彩色只给区域圆点。
5. 处处可见的 kbd chip（快捷键 hover 才显示，与 linear 相反）。
6. 小圆角复选框（正圆是 Things 的勾选记忆点）。
