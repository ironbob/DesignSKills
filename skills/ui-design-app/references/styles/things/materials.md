# Things 风格 · 表面体系（v0.x）

> 两个有版本边界的 profile：`classic-solid` 对应 OS 26 之前 Things 3；`os26-glass` 对应 Things 3.22 在 OS 26 的材质变化。共同身份是白净内容、宽松节奏与克制层级，不是“全界面玻璃”。

## 层级表

| 层 | classic-solid | os26-glass | 共同约束 |
| --- | --- | --- | --- |
| L0 内容画布 | `canvas` 实色白/近黑 | 同 classic | 内容永不玻璃化 |
| L1 侧栏 | `sidebar` 实色 + 右边框 | 半透明 sidebar + blur/saturate + 实色 fallback | 只露出少量环境色 |
| L1 小控件 | 实色/透明按钮 | 可按压控件允许轻微高光、scale 与更圆曲率 | 不改变功能语义 |
| L2 浮层 | `elevated` + border + 柔影 | 同类实色浮层，可有更柔高光 | 可读性优先 |
| L3 遮罩 | `scrim` | `scrim` | 不用彩色玻璃遮罩 |

## classic-solid 规则

1. 内容纯白，侧栏只深一档；面板之间用 1px border，不用阴影。
2. 阴影只属于 Quick Find、日期选择器、菜单等浮层。
3. 不使用 `backdrop-filter`；这是一个历史 profile，交付时必须标明不是 Things 3.22/OS 26 当前材质。

## os26-glass 规则

1. 只给 sidebar/chrome 使用克制 `backdrop-filter`；内容画布、todo 行和正文保持稳定实色。
2. 背景采样不足、Reduce Transparency、低性能或 Web 不支持时回退到 `--th-sidebar`。
3. 仅高价值小按钮可在 hover/press 使用极小 scale（建议不超过 1.02）和低 alpha glow；`prefers-reduced-motion` 下关闭 transform。
4. 曲率可以比 classic 略大，但 nested radii 必须同心，不能把所有容器做成胶囊。

## 浮层配方

```css
background: var(--th-elevated);
border: 1px solid var(--th-border);
border-radius: 10px;
box-shadow: var(--th-shadow);
animation: th-pop 180ms ease;
```

## 检查清单

- [ ] 是否明确选了 classic-solid 或 os26-glass，而不是混称？
- [ ] os26 的 glass 是否只停留在 sidebar/chrome？
- [ ] 内容、长文本和 todo 行是否仍有稳定实色背景？
- [ ] glow/scale 是否只用于可按压控件，且 reduced-motion 可关闭？
- [ ] 不支持 blur 时是否仍能读清边界和文字？
