# Figma 风格 · 控件规格库（v0.x）

> 实现见 `assets/styles/figma/figma-ui.css`（`.fig-shell` 作用域）。
> 数值为近似提炼，未经逐像素核对（v0.x）。

## 1. 状态语义（全控件）

| 状态 | 值 |
| --- | --- |
| 默认 | 透明底 + secondary 图标/文字 |
| hover | `fig-hover` 浅底 |
| 按压 | `fig-active` |
| 激活（工具） | `fig-active` 持续底 + 主文字（工具钮无蓝） |
| 选中（图层行） | `fig-selected` 蓝底 + **左缘 2px accent 条**（不反白） |
| 禁用 | opacity .4 + not-allowed |
| 焦点 | 2px 45% 蓝环，仅 :focus-visible |

过渡 100ms ease。

## 2. 控件清单

### 浮板（面板本体，materials.md 配方）

| 类 | 规格 |
| --- | --- |
| 顶工具条 | 水平居中悬浮，高 44、r12，内含工具钮组 + 缩放控件 + 分享钮 |
| 图层面板 | 宽 240-260，r12，顶部 tabs + 图层树 + 底部计数行 |
| 属性面板 | 宽 240-260，r12，顶部 tabs + 分节属性区 |

### 图标钮（工具/对齐/图层操作）

24×24、r6、14-16px 图标；hover 灰底、按压 `active`；
当前工具 = `active` 持续底（**不用蓝**——蓝只属于画布选中）。

### 数字输入（属性面板灵魂控件）

```css
.fig-num { height: 24px; width: 64px; border-radius: 6px;
  background: var(--fig-input-bg); font: 400 11px/1 ui-monospace, Menlo, monospace;
  font-variant-numeric: tabular-nums; }
```

- 结构：label（11px secondary）+ 值；**hover 时值区域出现 `ew-resize` 光标**——
  左右拖拽改值是身份交互（本包静态演示光标即可）。
- 聚焦 = `border-strong` + 蓝环；宽 56-72。
- 成组：X/Y 一行、W/H 一行，两列。

### 色板 swatch

- 圆点 12px、r999、1px `border`（透明色露灰白格可选）；
后接 HEX 值（11px mono）+ 不透明度（右对齐）。

### switch 开关

轨 26×14、r999；开 = `accent` 实底 + 白点；关 = `border-strong` 底；
点击 100ms。必须 `role="switch"` + `aria-checked`。

### 图层树

- 行高 28、r4；缩进 12px/级 + 嵌套竖参考线（1px `border`）。
- 行内：类型图标（frame 方框/组件**紫菱形** `--fig-component`/文字 T）+
  名称 12px + 右侧可见性眼睛/锁（hover 显隐）。
- 选中 = 蓝底 + 左缘 2px 蓝条；hover 灰底。

### tabs（图层/资产；设计/原型/检查）

高 28；激活项主文字 + 底部 2px `accent` 短线；未激活 secondary。

### 右键菜单

浮层配方（`overlay` + r8 + 小投影）；行 24、r4、hover 灰底；
快捷键右对齐 11px mono tertiary；分组 1px 分隔线。

### 分享/主按钮

高 24-28、r6、`accent` 实底白字（每屏至多 1 个）。

## 3. 画布选中态（不属于面板层）

- 选框：1.5px `accent` 描边（元素外扩 1px）。
- 手柄：8 个 7×7 方块，`--fig-handle-bg` 底 + 1px `accent` 边、r1。
- 尺寸标签：`accent` 实底白字 10px mono，位于选框下方居中：「W 240 H 120」。
- 间距参考线：红色（画布测量语义），面板 UI 不用红。

## 4. 反模式（figma 专属）

1. 贴边侧栏、面板共享边框——那是 linear；本风格浮板必须"离墙"。
2. 14px 正文、30+ 行高——微型化是身份；属性区 11px 起。
3. 蓝色用于工具激活/链接/按钮——蓝只属于画布选中与唯一分享钮。
4. 大面积品牌色/彩虹图标——Figma 彩虹只在 logo；组件紫只在图层树菱形。
5. backdrop blur、毛玻璃面板。
6. 把画布选框/手柄做进面板层（加面板投影）——它们属于 L0。
