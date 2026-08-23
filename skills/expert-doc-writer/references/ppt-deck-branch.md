# PPT 分支任务卡（阶段 5P–9P）

> 适用：`output=pptx` 或 `output=both`。前四阶段（写作情境/事实台账/故事线/表达形式规划）**完全复用**；从阶段 5 起走本分支。渲染底座：`ppt-renderer/`（与 doc-renderer 平级，职责只有 PPTX 生成/渲染/QA）。技术路线：JavaScript ES Module + pptxgenjs（原生可编辑 PPTX）；**禁止 python-pptx；禁止把网页截图/切页/HTML 转 PDF 塞进 PPT**。

## 数据层契约（跨端共享，防数字漂移）

```
docs/<日期>-<slug>/data/<slug>.facts.json       # 02 台账机器化：value/display/口径/source/置信(measured|derived|draft)
docs/<日期>-<slug>/data/<slug>.storyboard.json  # 每页：结论标题/证据/版式/notes(演讲稿+来源)/chart 或 flow 引用
```

- **数字纪律**：storyboard 文本数字一律 `{{F-x}}`（或 `.baseline/.value/.子字段`）插值；图表数值一律 `factValues`/`baselineFact` 引用。裸数字（日期/期间/编号白名单外）在 check-storyboard 直接 ERROR——这是"网页和 PPT 禁止各自维护数字"的执行机制：网页 `charts.ts` import 同一份 facts.json。
- **置信映射**：实测→measured、推算→derived、计划起草→draft（draft 条目须回填 02 台账，交付时列入待复核清单）。

## 阶段 5P · 定义演讲情境与 deck 规格

产物：storyboard.json 的 `deck` 段。默认决策（记 01 台账）：

| 字段 | 默认策略 |
|---|---|
| audience/purpose/minutes | 从 01 写作情境推导（述职类：向上汇报+资源申请，15 分钟） |
| aspect | 16:9 |
| template | 无用户模板时 null → ppt-renderer 默认 layout library；有模板时解包其 theme 作视觉约束（accent/ink/字体） |
| speakerNotes | true（口径/来源/假设/演讲稿全进 notes，页面只留结论+证据） |

完成标志：deck 段字段齐全，`minutes` 与页数匹配（约 1.5–2 分钟/页）。

## 阶段 6P · 生成 slide storyboard

产物：storyboard.json 的 `slides[]`。叙事规则（gate 强制）：

1. **一页一主结论**；标题必须是结论（中性标题黑名单：数据分析/项目进展/工作汇报/总结/概览…= ERROR）。
2. **按演讲节奏重排页序，不是文档节序切片**：参考链 = 标题 → 管理层摘要（结论→证据→风险→行动→ask 全路径预告）→ 分线证据（结论+数据图/机制图）→ 风险—行动 → 决策请求。
3. 每页 notes：`talk`（≥60 字演讲稿）+ `sources`（每条 non-trivial 事实的 F-x 口径）+ `gaps`（引用的 G-x）。
4. 计划/决策页（risk-action/decision-ask）：**Owner、截止、目标、基线、资源需求、"需要谁现在决定什么"** 全字段，缺一 = ERROR（决策闭环）。

## 阶段 7P · 选择版式、图表和视觉资产

- 版式库六种起步：`title` / `exec-summary` / `conclusion-chart` / `mechanism` / `risk-action` / `decision-ask`（注册表 `ppt-renderer/layouts/index.mjs`；新需求先扩版式库，不在单页上堆自由元素）。
- 图表选型与 web 端同判据（visual-form-catalog/chart-craft 仍适用）：同比对比→groupedBar/metricsBar；结构占比→stackedHBar；机制→mechanism 版式（原生形状+箭头）。**图表必须是 pptxgenjs 原生图表**（PowerPoint/WPS 里可编辑）。
- 反模式：dashboard 式卡片堆砌、每页多主结论、图例依赖、来源只写"内部数据"。

## 阶段 8P · 生成 PPTX、speaker notes、来源信息

命令（仓库根执行）：

```bash
node ppt-renderer/build-deck.mjs \
  --facts docs/<日期>-<slug>/data/<slug>.facts.json \
  --storyboard docs/<日期>-<slug>/data/<slug>.storyboard.json \
  --out docs/<日期>-<slug>/ppt [--template <用户模板.pptx>]
```

产物：`<slug>.pptx`（原生可编辑）+ `qa-report.{json,md}`。notes 由 facts 自动组装：每条引用事实带口径/来源/置信标记（推算/起草显式标注）。

## 阶段 9P · 逐页渲染 PNG 与视觉 QA

管线自动：PPTX → LibreOffice PDF → pdftoppm 逐页 PNG @150dpi。gate（check-slides + render-png）：

| 检查 | 方式 |
|---|---|
| 页数/标题落页/字号/文字密度/占位符 | 结构断言（几何模型 + pdftotext） |
| 元素重叠/越界/裁切/异常折行 | Placer 几何模型两两求交 + 折行高度估算 + PNG 边缘溢出像素检测 |
| 图表数字 = facts.json | 图表数据与 facts 原值逐项比对 |
| PPTX 与 PDF 一致 | pdftotext 逐页断言标题 |
| 视觉复核 | 逐页查看 png/（多模态读图或人工），结论登记进 qa-report.md 的「视觉复核记录」段 |

**定稿条件**：qa-report 判定 PASS（ERROR=0）且视觉复核无未处置问题。渲染环境依赖：LibreOffice（`soffice`）+ poppler（`pdftoppm`/`pdftotext`）；Keynote AppleScript 在部分 macOS 环境被自动化权限卡死（-1712），勿依赖。

## 与 web 分支的并行关系（output=both）

- 两端共用阶段 1–4 与 data/ 数据层；阶段 5 起各自走 5–8（web）与 5P–9P（ppt），互不阻塞。
- web 端 `charts.ts` 必须 import facts.json 取数（模板见 h1-mkt-ops-2026.charts.ts 的写法）。
- 改数的唯一入口：02 台账（回填）→ facts.json → 两端各自重渲染；任何一端直改数字 = 违约。
