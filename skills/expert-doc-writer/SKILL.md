---
name: expert-doc-writer
description: "Trigger only when the user explicitly asks to use this skill by name: `$expert-doc-writer`, `expert-doc-writer`, or a namespaced form ending in `:expert-doc-writer`. Do not trigger from task similarity, writing, document, report, or tech-proposal keywords, repository contents, or inferred intent. Runs the eight-stage expert writing workflow (context → evidence ledger → storyline → media plan → theme preset → chassis components → sectioned drafting in markdown + component data → assemble + build + crit) as one autonomous run: stage gates are automatic, key choices follow default-decision policies recorded in a decision ledger, and there are no mid-flow confirmation pauses (the only allowed pause: one minimal blocking question when topic/reader/any source material is missing). Produces a final VitePress-rendered document (ECharts data charts and Mermaid diagrams via the doc-renderer component chassis) delivered with PDF, process ledger, verification results, adopted assumptions, and open risks."
---

# expert-doc-writer：八阶段专家写作工作流

## 目的

把一份写作需求（**技术方案 / 汇报文档**）变成**框架渲染的成稿站点**——把事情讲清楚，且页面表现力到位：流程是图不是文字墙，数据是图表不是数字段落，论证是短文字不是装饰。工作法来自人类专家的真实实践（想清楚给谁看→盘弹药→排故事线→选表达形式→定视觉→关键节先写→组装→读者视角自审），**不是**"跳过规划把素材丢给 AI 直接生成全文"——八个阶段每个都做，只是由 AI 在一次执行中连续走完，不等人工确认。

**渲染底座**：制作阶段（5–8）跑在 `doc-renderer/`（VitePress + 组件库 KpiRow/FigureChart/Callout/CompareMatrix + chartTheme 统一图表主题层）。表现力的稳定性来自底座：图表观感一处注入、排版由框架引擎、对齐由组件构造——不靠每篇手写手调。

本 skill 存在的理由（要稳定根治的三个病）：

1. 数据内容写成数字罗列段落 → 阶段 4 形式规划 + CHART 查
2. 流程内容写成大段文字 → Mermaid 结构图 + WALL 查
3. 图表有但不可读（中性标题、图例依赖、无来源） → chart-craft 工艺六维

三个与生俱来的约束：

1. **一次执行、自动决策**：八阶段连续执行，阶段 gate 全绿即自动推进，全程不暂停等人工确认。论点、故事线、主题档位、表达形式等关键选择由**默认决策策略**自动选定，候选、选定项、理由、置信度记入 `01` 决策台账（`deviations.md` 同步记执行偏差）——**审阅发生在交付之后，不阻塞生成**。唯一允许的暂停：缺文档主题 / 目标读者 / 任何可识别素材时，提**一个**最小阻塞问题。
2. **中间产物是消耗品，成稿与台账是契约**：渲染站点（`doc-renderer/docs/<slug>/` + 图表数据层）+ `02-事实台账.md` 是契约；其余过程文件可扔可改。
3. **表现力来自形式与内容匹配，不来自装饰**：先判定内容类型再选形式（visual-form-catalog）；文字是最贵的形式，只留给论证。

## 工作区契约（磁盘是唯一真相源）

过程产物在 `<workspace>/`（`docs/<日期>-<slug>/`），渲染内容在底座 `doc-renderer/docs/<slug>/`：

```
<workspace>/                      # 过程（00–04 为规划契约，05+ 为记录）
  00-brief.md … 04-表达形式清单.md   # 规划产物（与渲染底座无关，纯思考层）
  06-组件覆盖映射.md                # 阶段 6 组件映射记录
  deviations.md                    # 干跑/执行偏差日志（持续记）
  08-findings.md                   # crit 审计记录
  09-交付说明.md                    # 站点/PDF/口径/可推翻决策/假设与风险/验证结果
  05-style-tiles/ 07-draft/ …      # 可选过程记录（样张/草稿截图与 md 副本）

doc-renderer/docs/<slug>/          # 内容（阶段 7–8 的工作对象；交付时只含 index.md + sections/）
  index.md                         # 组装页：doc-head + 数据 import + @include 各节
  sections/s1.md … sections/sN.md  # 分节：h2{#锚点} + p.lead + 组件 + mermaid
doc-renderer/.vitepress/data/<slug>.charts.ts   # 图表数据层（与 02 台账同源）
```

## 阶段总表

| # | 阶段 | 产物 | 默认决策（AI 自动，记台账） | gate |
|---|---|---|---|---|
| 1 | 写作情境 | 01：读者画像+论点+决策清单+台账骨架 | 论点/文种：候选中按素材成案意图选定 | check_plan 1 |
| 2 | 事实台账 | 02：事实表+缺口清单 | G-x 处置：降级表述→放弃→去挖（默认序） | check_plan 2 |
| 3 | 故事线 | 03：论证链+章节骨架 | 故事线：默认结论先行；零素材节=推算+『推断』标注 | check_plan 3 |
| 4 | 表达形式规划 | 04：media plan | 形式：目录规则自动选型；预算失衡自动回 3 | check_plan 4 |
| 5 | 视觉方向·主题档位 | 底座 presets ×2 + 最小真实样张双档对比 | 档位：按 01 阅读场景映射选定 | check_doc --md --lite |
| 6 | 排版系统·组件档 | 组件覆盖映射 + 图型构造器 + 样张 | 组件映射/新组件 props 自动定 | 组件完备性自检 |
| 7 | 分节成稿 | sections/sN.md + 数据层（★节先写先自检→铺全量） | 无人工节点：★节过 gate 即铺开 | check_doc --md |
| 8 | 组装+构建+crit+定稿 | index.md + build + findings + 09 | crit 处置：🔴必修/🟡修复或豁免，自动定稿 | 🔴清零 + check_doc --md + build 0 退出 + DOM 实测 |

每阶段执行前**加载对应 `references/stage-0N-*.md` 任务卡**（含产物模板、完成标志、坑）。

**Gate 完整命令**（仓库根执行；`<ws>`=workspace 目录 `docs/<日期>-<slug>/`，`<slug>`=文档 slug）：

```bash
python3 skills/expert-doc-writer/scripts/check_plan.py <ws>/ 1 2 3 4   # 阶段 1–4 规划 gate（可单阶段：… 1）
python3 skills/expert-doc-writer/scripts/check_doc.py doc-renderer/docs/<slug>/ --md              # 阶段 7/8 源文件七查（全量）
python3 skills/expert-doc-writer/scripts/check_doc.py doc-renderer/docs/<slug>/style-probe.md --md --lite   # 阶段 5 样张 COPY 查
cd doc-renderer && npm run build && npm run preview                     # 阶段 8 构建 + 预览（DOM/像素实测载体）
```

<HARD-GATE>
1. **一次执行直达终稿**：八阶段连续执行，阶段 gate 全绿 + 默认决策入台账即自动推进，中途不提问、不等待。所有默认决策（论点、故事线、形式清单、档位、G-x 处置、crit 豁免）当日追加进 `01` 决策台账（含候选、选定、理由、置信度），交付时在 `09` 集中列出可推翻项。唯一允许的暂停：缺文档主题 / 目标读者 / 任何可识别素材 → 一个最小阻塞问题。
2. **成稿必须过双重 gate**：源文件 `check_doc.py docs/<slug>/ --md` 七查全绿（ERROR 无豁免）；`npm run build` 0 退出 **且 DOM 实测**（ECharts/Mermaid SVG 计数对得上、降级文本 0 外露）——构建成功 ≠ 渲染成功。
3. **crit 🔴 清零才定稿**：六维（该图不图/图型匹配/标题即结论/扫读链/来源口径/图表工艺）每维必有结论，🔴 必修，🟡 必处置（修复/豁免记录）。处置由 AI 自动执行并留痕，不等待人工审批。
4. **数字必须可溯源**：成稿与数据层每个数字 ⊆ `02-事实台账`；新数字先回填台账（含来源与口径）再入稿，编造=🔴。数据缺失不得编造、也不得变成阻塞提问：走 G-x 降级（保守表述 + 『待核实』标记）或放弃该论证，继续完成可交付版本。
5. **结构改动回阶段 3/4 备案**：成稿期发现故事线/形式问题，回写 `03`/`04` 并记 P-x 进台账后才改稿，不允许只改渲染内容。
</HARD-GATE>

## 工具分工红线

| 工具 | 只用于 | 禁止 |
|---|---|---|
| Mermaid（底座插件渲染） | 结构图：flowchart / sequence / state / 架构分层 | 画数据图（含 xy-chart） |
| ECharts（经 FigureChart + chartTheme） | 数据图：柱 / 折线 / 堆叠 / 散点 | 结构图；option 写颜色/字号裸值绕过 withTheme |
| 组件（KpiRow/CompareMatrix/Callout） | 指标总览 / 对比矩阵 / 论断框 / 清单表 | — |
| 纯文字 | 论证因果、动机、取舍 | 流程叙述、数字罗列 |

## 反模式

| 反模式 | 正确做法 |
|---|---|
| 大段文字描述流程 | Mermaid flowchart/sequence |
| 数字罗列成段落 | 按数据类型选 ECharts 图或表 |
| 中性图题（"图1：对比"） | 标题即结论（"构建时间下降 62%"） |
| 靠图例+悬停才能读懂 | 直接标注 |
| 论证也硬画成图 | 短段落 + Callout |
| 无来源数字 | 事实台账 + FigureChart source 口径 |
| 跳过规划直接生成全文 | 八阶段全程执行，关键节先行（自动推进，不等确认） |
| 表现力=装饰（渐变/图标堆砌） | 表现力=形式匹配 + 图表工艺 |
| Mermaid 画数据趋势 | ECharts |
| option 手配颜色/字号 | chartTheme.withTheme 统一注入 |
| 构建通过就交付 | DOM 实测渲染计数 |

## 参考资源

- **`references/stage-01-context.md` … `stage-08-assemble-crit.md`** —— 八张阶段任务卡。**逐阶段加载**。
- **`references/visual-form-catalog.md`** —— 内容类型→表达形式目录（T1–T13：判定信号/模板/反例）。**阶段 4 必读**。
- **`references/chart-craft.md`** —— 图表工艺：结论式标题/直接标注/去垃圾/色彩纪律/两点不画折线。**阶段 5/7 出图前必读**。
- **`references/doc-conventions.md`** —— 渲染底座公约：目录分工/组件用法/图表纪律/构建交付。**阶段 5/6/7/8 必读**。
- **`scripts/check_plan.py`** —— 阶段 1–4 规划产物完整性/覆盖 gate（论点须已按默认策略选定；A-x 须台账 ✅ 标记才算已答复）。
- **`scripts/check_doc.py`** —— 产物七查 gate（`--md` 查底座源文件 / 默认查 HTML）。**阶段 5（lite）/7/8（全量）完成前必须运行**。
- **渲染底座**：`doc-renderer/`（VitePress + 组件库 + chartTheme；README 有架构与 spike 验证记录）。**阶段 5 起的工作对象**。
- **参照示例（金标准）**：完整一次执行 `docs/2026-08-23-danci-data-layer/`（00–09 全套规划/记录 + deviations 10 条 + 交付 PDF）+ 渲染层 `doc-renderer/docs/danci-data-layer/`（index + sections/s1–s7 + `.vitepress/data/danci.charts.ts`，两 gate 均 PASS）。渲染层第二参照：`doc-renderer/docs/q3-ops-2026/` + `docs/2026-08-23-q3-ops-report/deviations.md`（12 条，skill 校准史；其规划件已清理，不作规划层参照）。模板与金标准的差异=通用化改动。

## 边界

- **文种**：技术方案、汇报文档（阶段 3 分叙事模板）；散文/营销文案/学术论文不在范围。
- **规模**：单文档 ≤12 节；超限先拆。
- **素材前提（最小阻塞策略）**：缺文档主题、目标读者或任何可识别素材 → 提**一个**最小阻塞问题后等待；普通素材缺口（部分数据/口径/背景不全）不提问、不编造 → B-x 默认假设 + G-x 降级（保守表述 / 『待核实』标记），交付时集中列出。
- **环境**：Node 18+（底座构建依赖）；无网投屏场景走打印 PDF。
- **修改四层级**：内容（sections/sN.md 文字/charts 数据）/组件（底座换件扩展）/结构（回阶段 3）/风格（改主题档位/变量重出）。
