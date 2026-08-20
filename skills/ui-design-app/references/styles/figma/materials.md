# Figma 风格 · 表面体系（v0.x）

> 与 linear 相反：**面板不贴边、不靠边框分层，而是实色浮板 + 大而柔的投影，"漂浮"在灰画板上**。
> 无 backdrop blur。数值为近似提炼，未经逐像素核对（v0.x）。

## 层级表

| 层 | 表面 | 亮 | 暗 | 投影/边框 |
| --- | --- | --- | --- | --- |
| L0 画板 | `canvas` | `#b3b3b3`（经典 Figma 灰） | `#262626`（比面板深） | 网格点 `grid-dot` 1px |
| L1 浮板 | `panel` | `#ffffff` | `#2c2c2c` | r12 + 1px `border` + **面板大投影** |
| L2 浮层 | `overlay` | `#ffffff` | `#1e1e1e`（比面板深一档） | r8 + `border` + 小投影 |
| L3 模态遮罩 | `scrim` | `rgba(0,0,0,.45)` | `rgba(0,0,0,.65)` | 遮罩上叠 L2 |
| — Tooltip | `tooltip-bg` | `#1e1e1e`（两主题都深色） | `#0f0f0f` | 小投影，r4 |

画布元素（蓝色选框、8 个白手柄、尺寸标签、间距参考线）**不属于面板层**——
它们直接画在 L0 上，不带面板投影。

## 规则

1. **投影即层级**：浮板必须同时有边框 + 大柔投影（`0 12px 32px` 级），
   缺投影就变成 linear 的贴边面板，身份即失。
2. **面板间留 8px 灰缝**：工具条/图层面板/属性面板互不接触，缝隙露出画板灰。
3. 亮色画板是**中灰**（#b3b3b3），不是白——白色画板会把浮板"淹没"。
4. 暗色画板比面板**深**（#262626 vs #2c2c2c），与 linear"逐级变亮"方向相反。
5. **禁止**：backdrop-filter、贴边侧栏、面板间共享边框。

## 浮板配方（所有面板的唯一材质）

```css
background: var(--fig-panel);
border: 1px solid var(--fig-border);
border-radius: 12px;
box-shadow: var(--fig-shadow); /* 见 tokens.md §5 */
```

浮层（菜单/弹层）把 `panel`→`overlay`、r12→r8、`shadow`→`shadow-sm`，
出现动画 `120ms`（opacity + translateY(4px)）。Tooltip 实色深底 + r4 + 小投影。
