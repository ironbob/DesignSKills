# Things 风格 · 表面体系（v0.x）

> 全实色、**零模糊**。这是与 finder（vibrancy）最决绝的差异，也是与 linear 的共同点；
> 但 Things 的实色是「白净 + 柔和大投影」，linear 的实色是「灰阶 + 硬边框分层」。

## 层级表

| 层 | 表面 | 亮 | 暗 | 边框 |
| --- | --- | --- | --- | --- |
| L0 内容画布 | `canvas` | `#ffffff` | `#2b2b2e` | 无 |
| L1 侧栏 | `sidebar` | `#f4f4f6` | `#212123` | 右 1px `border` |
| L2 浮层 | `elevated` | `#ffffff` | `#323236` | 四边 1px `border` + 柔和大投影 |
| L3 遮罩 | `scrim` | `rgba(0,0,0,.35)` | `rgba(0,0,0,.50)` | 遮罩上叠 L2 |

## 规则

1. **亮色为默认人设**：内容区纯白，侧栏只比白深一档（#f4f4f6）；禁止再细分层。
2. **边框优先于阴影**（面板之间）；阴影只属于浮层——且是「柔和大投影」（8px 24px），
   比 linear 的浮层投影更大更软，营造"轻轻放在纸面上"的 Apple 观感。
3. **禁止**：backdrop-filter、半透明面板、毛玻璃、彩色玻璃描边。
4. 面板间不用阴影；选中态是弱蓝底叠加（`--th-selected`），不改变表面层级。

## 浮层配方（唯一用阴影的表面）

```css
background: var(--th-elevated);
border: 1px solid var(--th-border);
border-radius: 10px;                 /* 比 linear 的 8 更圆润 */
box-shadow: var(--th-shadow);        /* 柔和大投影，见 tokens.md §6 */
animation: th-pop 180ms ease;        /* opacity 0→1 + translateY(6px)→0 */
```

适用：快捷查找（⌘F）、日期选择器、右键菜单（macOS 实色菜单：灰底 hover，
**不用蓝底反白**——与 finder 的 NSMenu 高亮也不同，Things 菜单更素）。

## 检查清单

- [ ] 页面里除浮层外搜不到 box-shadow？
- [ ] 搜不到 backdrop-filter / blur？
- [ ] 侧栏与内容只用 1px border 分界？
- [ ] 浮层投影用的是 --th-shadow（柔和大投影），不是硬阴影？
