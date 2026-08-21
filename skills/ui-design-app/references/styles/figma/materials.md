# Figma 风格 · 表面体系（v0.x）

> 正式 UI3 使用中性画板、停靠面板、底部浮动工具条和上下文浮层。无 backdrop blur。数值为 derived，版本依据见 `evidence.md`。

## 层级表

| 层 | 表面 | 亮 | 暗 | 投影/边框 |
| --- | --- | --- | --- | --- |
| L0 画板 | `canvas` | `#b3b3b3` | `#262626` | 可选网格点，不作网页背景装饰 |
| L1 停靠面板 | `panel` | `#ffffff` | `#2c2c2c` | 与画板 1px 边界；默认无大投影 |
| L1.5 底部工具条 | `panel` | 同上 | 同上 | r12 + border + `shadow` |
| L2 浮层 | `overlay` | `#ffffff` | `#1e1e1e` | r8 + border + `shadow-sm` |
| L3 模态遮罩 | `scrim` | `rgba(0,0,0,.45)` | `rgba(0,0,0,.65)` | 遮罩上叠 L2 |
| — Tooltip | `tooltip-bg` | `#1e1e1e` | `#0f0f0f` | r4 + 小投影 |

画布选择框、手柄、尺寸标签和参考线直接画在 L0，不继承面板阴影。

## 规则

1. 停靠面板主要靠实色差与共享边界组织；大柔投影只给底部工具条、Minimize UI 临时面板和浮层。
2. 画板与 panel 保持足够差异；暗色画板通常比面板深。
3. 面板可折叠/调宽；临时浮动时才使用 8-12px 外间距、r12 和 `shadow`。
4. overlay 比 panel 更明确，菜单/Actions/modal 不能与永久面板同层。
5. 禁止 backdrop-filter；不要把画布内容卡片化或给选择手柄加投影。

## 配方

停靠面板：

```css
background: var(--fig-panel);
border-inline: 1px solid var(--fig-border);
border-radius: 0;
box-shadow: none;
```

底部工具条/临时浮板：

```css
background: var(--fig-panel);
border: 1px solid var(--fig-border);
border-radius: 12px;
box-shadow: var(--fig-shadow);
```

菜单/Actions 使用 `overlay`、r8、`shadow-sm`，以约 120ms opacity + translateY 进入。
