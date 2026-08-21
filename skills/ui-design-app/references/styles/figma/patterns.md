# Figma 风格 · 布局与交互模式（v0.x）

> 灰画板 + 停靠面板 + 底部工具条只适用于画布/创作工具，是 `archetype-bound` 母题。正式 UI3 默认不是三块永久浮板；浮动面板仅用于 Minimize UI、FigJam、Slides grid 等兼容上下文。

## 1. 应用骨架（正式 UI3）

```text
┌────────────┬────────────────────────────┬────────────┐
│ 左·图层    │                            │ 右·属性    │
│ docked     │          灰画板            │ docked     │
│ resizable  │       canvas / work        │ resizable  │
│            │                            │            │
│            │      [ 底部 slim toolbar ] │            │
└────────────┴────────────────────────────┴────────────┘
```

- 左右面板停靠、可折叠、可调宽；画布占据剩余空间。
- 底部工具条浮在画布上，保留常用工具与模式入口；不要放回旧式顶部工具条。
- Minimize UI 可隐藏面板并按选择临时显示属性区；这时面板可以浮动，但必须是模式结果而非默认构图。
- 窄窗（<768）面板退为 overlay drawer/边缘入口，不能把画布压到不可用。

## 2. 键盘流（模式切换 + Actions）

- 单键工具只在目标确有工具模式时采用；输入框、文本编辑和组合输入期间必须抑制。
- Actions menu 承担跨功能检索；它与单键工具并存，不能用一排装饰 kbd chip 代替真实命令。
- `Esc` 层层退出：关菜单 → 退出临时面板/编辑 → 取消对象选择。
- 属性数字输入可支持 ↑↓ 微调、⇧↑↓ 放大步进；只有连续数值编辑才支持水平拖拽改值。

## 3. 交互节奏

- 弹层/菜单约 120ms、选择框显隐约 80ms；拖拽与数值修改即时反馈。
- 工具 active 用中性底，对象 selected/focus 用蓝；两者不能混为一种状态。
- labels 可以按空间和熟练度显隐，但图标按钮始终有 accessible name/tooltip。

## 4. 主题

`data-theme="dark|light"` 双主题参考；组件只消费 token。目标产品没有双主题时不擅自增加。

## 5. 与 linear / geist / finder 的互换决策

| 要做的东西 | figma UI3 | linear | geist / finder |
| --- | --- | --- | --- |
| 面板布局 | docked/resizable + 可折叠；特定模式才浮动 | 导航与内容 chrome | 贴边侧栏/平台窗口 |
| 工具条 | 画布底部 slim toolbar | 顶部/上下文动作 | 平台 toolbar / 页面 action |
| 控件尺寸 | 24-28 微型、11-12px | 26-32、13px | 28-32、13-14px |
| 选择语义 | 蓝=画布对象/当前项 | 单 accent=列表/动作 | profile/platform accent |
| 工具激活 | 中性灰 active | accent active | 依控件语义 |
| 键盘范式 | 单键模式 + Actions | 命令菜单 + 快捷键 | 菜单/命令入口 |

**反模式**：把 beta floating panels 写成正式 UI3 默认；把普通列表产品改成画布；大面积品牌色；工具 active 与对象 selected 都涂蓝；为相似度伪造工具快捷键。
