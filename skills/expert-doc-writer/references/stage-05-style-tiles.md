# 阶段 5：视觉方向 · 主题档位（任务卡）

## 目的

定**文档的气质**——载体是渲染底座（doc-renderer），视觉方向 = **主题档位**：同一节真实内容，用两套主题变量档各渲染一遍，拉开气质差异。不再手写 tile HTML。

## 输入

`01` 阅读场景（投屏远读 vs 会前细读 → 直接影响档位）+ `04` 形式清单（档位样本必须覆盖将用到的组件族）。

## 产出

- 底座 `theme/presets/` 下两个**主题档位**（CSS 变量集，如 `presets/brief.css` 简报档 / `presets/editorial.css` 编辑档；底座已有则直接复用，不必新造）；
- **最小真实样张**：从 `02` 台账取真实数字与真实文案，拼一页样张（1×KpiRow + 1×FigureChart + 1×mermaid + 1×矩阵或 callout）——正式分节内容是阶段 7 的产物，此处**不依赖它**，也**绝不许 lorem/假数字**；样张页临时放 `doc-renderer/docs/<slug>/style-probe.md`，`npm run build && npm run preview` 下双档渲染对比（`body[data-doc-preset]` 页内切换或两处各挂一档）；
- 对照说明一行：决策问题与选定结论（例："投屏述职 → 选简报档，理由：…"）；
- **样张善后（时序闭环）**：档位选定后，样张要么升级为正式 `sections/s1.md` 的素材，要么从 `doc-renderer/docs/<slug>/` 删除（md 副本 + 双档截图归 workspace `05-style-tiles/`）——交付时渲染目录只含 `index.md + sections/`。

档位轴参考（选 2 个拉开差异）：

| 档位 | 变量特征 | 适合 |
|---|---|---|
| 简报档 | 大数字 KPI、高对比、卡片分区、宽版心 | 投屏远读、汇报文档 |
| 编辑档 | 衬线标题、细规则线、窄版心、密排 | 会前细读、存档、技术方案 |
| 技术档 | 等宽点缀、密集信息、深色代码区 | 接口/架构重的技术方案 |

要求：

1. 档位只动**主题变量与档位级样式**（`--doc-*` / `--vp-c-brand-*` / 版心/字阶），不动组件结构——一致性由构造保证；
2. 真实数据真实文案（lorem = FAIL）；
3. print 预览不断版（底座已带打印 CSS，档位不得破坏）。

## 完成标志

两档在样张上渲染成功（build+preview 实测；**dev 模式有 fastdom ESM 已知问题，不用于验证**）且差异在气质；`python3 skills/expert-doc-writer/scripts/check_doc.py doc-renderer/docs/<slug>/style-probe.md --md --lite`（COPY 查）全绿；档位已选定并记台账（候选、选定、理由、置信度）。

## 默认决策策略

**档位按 `01` 阅读场景自动映射**：投屏远读→简报档；会前细读/存档→编辑档；接口/架构重的技术方案→技术档。混搭仅当选定档有单点明确缺陷（如编辑档字阶 + 简报档对比度），混搭内容记台账。台账记："阶段 5 决策：档位=X（候选、理由、置信度）"。

## 坑

- 档位样本用假文案——气质判断失真；
- 只给色板不给成文渲染——色板推不出阅读体验；
- 档位间差异是"换个色"而非层级/密度策略差异（假档位）。

## 工具化要点

- 底座机制：主题档位 = CSS 变量集 + 切换开关（未来网页工具即"档位切换器"）。
- gate：`python3 skills/expert-doc-writer/scripts/check_doc.py doc-renderer/docs/<slug>/style-probe.md --md --lite` 为完成条件；档位渲染成功由 build+preview 保证。
