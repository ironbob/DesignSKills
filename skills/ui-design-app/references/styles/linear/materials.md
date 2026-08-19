# Linear 风格 · 表面体系（v0.x）

> 与 finder 相反：**无 vibrancy、无 backdrop blur**。分层全部实色 + 1px 边框，
> 只有浮出内容才允许阴影。这一节是"材质"概念的实色等价物。

## 层级表

| 层 | 表面 | 亮 | 暗 | 边框 |
| --- | --- | --- | --- | --- |
| L0 画布 | `canvas` | `#ffffff` | `#08090a` | 无 |
| L1 面板 | `surface` | `#f9f9fa` | `#0f1011` | 上/右 1px `border`（相邻面板之间） |
| L2 浮层 | `elevated` | `#ffffff` | `#16181d` | 四边 1px `border` + 浮层阴影 |
| L3 模态遮罩 | `rgba(0,0,0,.45)` | `rgba(0,0,0,.65)` | — | 遮罩上再叠 L2 |

## 规则

1. **色差即层级**：暗色系 L0→L2 逐级变亮（#08090a → #0f1011 → #16181d）；
   亮色系靠灰度 + 边框。禁止在同一层里再细分灰度。
2. **边框优先于阴影**：面板交界用 1px 边框；阴影只属于浮层（菜单/弹层/命令面板/Tooltip）。
3. **禁止**：backdrop-filter、半透明面板、毛玻璃——实色是这风格的效率感来源。
4. 遮罩下内容允许被辨认为"还在那里"（遮罩透明度 0.45-0.65），与 finder Sheet 的
   "不可辨认"要求不同。

## 浮层配方（唯一用阴影的表面）

```css
background: var(--ln-elevated);
border: 1px solid var(--ln-border);
border-radius: 8px;
box-shadow: var(--ln-shadow); /* 见 tokens.md §5 */
animation: ln-pop 120ms ease; /* opacity 0→1 + translateY(4px)→0 */
```

菜单行 hover = `--ln-hover` 浅底（**不是** finder 的蓝底白字高亮——Linear 菜单高亮是灰底，
紫只给选中项的对勾/图标）。
