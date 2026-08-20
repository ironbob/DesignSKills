# Geist 风格 · 表面体系（v0.x）

> 与 linear 同为实色分层，但气质更"冷、硬、几何"：亮色以 #ffffff 画布 + #eaeaea 细线
> 分层；暗色以**真黑 #000000** 画布逐级抬升（Geist 签名）。无 backdrop blur。
> 数值为近似提炼（v0.x）。

## 层级表

| 层 | 表面 | 亮 | 暗 | 边框/影 |
| --- | --- | --- | --- | --- |
| L0 画布 | `canvas` | `#ffffff` | `#000000` | 无 |
| L1 次表面 | `surface` | `#fafafa` | `#0a0a0a` | 1px `border`（侧栏右缘/表格内衬） |
| L2 卡片 | `elevated` + 描边影 | `#ffffff` | `#111111` | 1px `border` + `--ge-shadow-sm` |
| L3 浮层 | `elevated` + 大柔影 | `#ffffff` | `#111111` | 1px `border` + `--ge-shadow` |
| L4 模态遮罩 | `--ge-scrim` | `rgba(0,0,0,.5)` | `rgba(0,0,0,.65)` | 遮罩上叠 L3 |

## 规则

1. **真黑画布**：暗色 L0 就是纯 #000000，L1/L2 只做 +0a/+11 的极小抬升——
   层级感主要靠边框，不靠灰度差。
2. **细线是主角**：#eaeaea（亮）/ #262626（暗）1px 边框承担几乎全部分层；
   卡片额外加 1px 描边影让白卡浮出白画布。
3. **禁止**：backdrop blur、半透明面板、彩色渐变大色块、暖灰（#faf9f7 一类）。
4. 遮罩下内容允许被辨认（0.5-0.65），命令面板浮于其上居中偏上。

## 浮层配方（菜单 / ⌘K 命令面板 / Tooltip）

```css
background: var(--ge-elevated);
border: 1px solid var(--ge-border);
border-radius: 8px;
box-shadow: var(--ge-shadow);        /* 0 8px 30px，Geist 标志性大柔影 */
animation: ge-pop 150ms ease;        /* opacity + scale(.98)→1 */
```

菜单行 hover = `--ge-hover` 灰底（不是蓝底）；选中项 = `--ge-selected` 灰底 +
accent 文字。Tooltip 固定深底（亮色主题下也用深灰底白字，开发者工具气质）。

## 状态 pill（唯一彩面）

淡彩底（`--ge-*-bg`）+ 深彩字（`--ge-*`）+ 6px 状态点；Building 点带脉冲动画。
这与 linear 的"禁止彩色底"相反——Geist 允许状态语义用色，但仅限 pill 这一处。
