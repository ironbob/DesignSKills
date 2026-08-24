# ppt-renderer

`expert-doc-writer` 的 **PPTX 渲染底座**——与 `doc-renderer/` 平级、职责单一：只做 PPTX 生成、渲染与 QA。网页文档渲染仍在 `doc-renderer/`，两边不共享构建逻辑，只共享**数据层**。

## 架构契约

```
docs/<日期>-<slug>/data/<slug>.facts.json        ← 唯一数字源（02 台账机器化）
docs/<日期>-<slug>/data/<slug>.storyboard.json   ← 每页：结论/证据/版式/notes/来源
        │
        ▼
ppt-renderer/build-deck.mjs
  ├─ checks/check-storyboard.mjs    gate 1：schema/结论式标题/决策闭环/裸数字禁令
  │                                      + 演讲可读性：内容预算/结论—证据一致性/版式语义（超预算=ERROR）
  ├─ builders/theme.mjs             模板视觉约束（--template 时解包 theme1.xml）
  ├─ builders/deck.mjs + layouts/   storyboard → pptxgenjs 原生可编辑元素
  │    layouts/：title / exec-summary / conclusion-chart / mechanism / risk-action / decision-ask / roadmap
  │    layouts/budgets.mjs：各版式内容预算/条数容量/screenPoints/主视觉 factRefs 推导（QA 契约）
  ├─ checks/check-slides.mjs        gate 2：几何模型（重叠/越界/折行/字号/占位符/图表数字=facts）
  │                                 + 投屏可读性：标题≤2行/反shrink-to-fit/主视觉占比/文字面积/留白/卡片数/缩略图关键元素
  └─ checks/render-png.mjs          gate 3：LibreOffice PDF → pdftoppm PNG → 边缘溢出像素 + pdftotext 断言
        │
        ▼
docs/<日期>-<slug>/ppt/
  <slug>.pptx  <slug>.pdf  png/slide-*.png  qa-report.json  qa-report.md
  qa-visual-review.json             视觉复核评分卡（人工/AI 逐页 1–5 分；任一维 <4 整 deck FAIL，复核后重跑 build 生效）
```

## 用法

```bash
node ppt-renderer/build-deck.mjs \
  --facts    docs/<日期>-<slug>/data/<slug>.facts.json \
  --storyboard docs/<日期>-<slug>/data/<slug>.storyboard.json \
  --out      docs/<日期>-<slug>/ppt \
  [--template <用户模板.pptx>]     # 提取模板 accent/ink/字体作视觉约束
  [--no-pdf]                        # 只出 PPTX + 结构 QA（无渲染 QA）
```

退出码：0 = QA PASS；1 = 任一 gate ERROR（构建前拦截 storyboard 问题，构建后输出 qa-report 并失败退出）。

## 硬约束（为什么这样写）

1. **数字防漂移**：storyboard 文本数字一律 `{{F-x}}` / `{{F-x.baseline}}` 插值，图表数值一律 `factValues` 引用；`check-storyboard` 对裸数字（白名单：日期/期间/编号除外）直接 ERROR。网页端 `charts.ts` 同样 import 这份 facts.json——两端不可能各自维护数字。
2. **可编辑**：图表用 pptxgenjs **原生图表**（OOXML chart part），流程用**原生形状+箭头**，不是截图、不是 HTML 转 PDF 塞进 PPT。
3. **渲染 QA 与几何 QA 双保险**：Placer 记录每个元素的几何（与渲染同源），check-slides 用它做重叠/越界/折行估算；render-png 再用真实渲染（PDF/PNG）验证页数、标题落页、边缘溢出。
4. **speaker notes 是口径的家**：页面只有结论+必要证据；口径、来源、假设、推算标记、演讲稿全在 notes（`builders/notes.mjs` 自动从 facts 组装）。
5. **环境依赖**：Node 18+、LibreOffice（`soffice`，PPTX→PDF）、poppler（`pdftoppm`/`pdftotext`）。Keynote AppleScript 在部分 macOS 环境会被自动化权限卡死（-1712），不要依赖。

## 版式库（七版式）

| layout | 用途 | 决策闭环字段 | 版式语义红线 |
|---|---|---|---|
| `title` | 标题页（deck 标题+结论副标） | — | — |
| `exec-summary` | 管理层摘要（论点+KPI 栅格+ask 预告） | — | thesis/risks/kpis/ask 四模块并存时 thesis ≤48 字 |
| `conclusion-chart` | 结论+数据图（左图右要点） | — | takeaways ≤2，右栏禁长段落（单条 ≤60 字） |
| `mechanism` | 机制/流程（双排原生形状流程+运行结果条） | — | rows ≤3，每行 steps ≤4 |
| `risk-action` | 风险—行动（左问题右行动，箭头连接） | action.owner/deadline 必填 | pairs ≤2 |
| `decision-ask` | 决策请求/资源申请（请求卡+蓝条 ask） | requests[] 全字段+askLine 必填 | **requests ≤2**（无紧凑三卡模式） |
| `roadmap` | 规划路线（≤3 工作流：what·里程碑·Owner） | — | 禁 target/baseline/resources/requests/askLine（属 decision-ask） |

新增版式：在 `layouts/` 加文件、`layouts/index.mjs` 注册；所有放置走 `Placer`（自动纳入几何 QA）。
版式须导出契约：`FONT_SPEC`（元素设计字号，反 shrink-to-fit 断言）、`HERO_NAMES`（主视觉元素，占比 ≥35%）、`KEY_ELEMENTS`（缩略图关键元素字号/加粗下限）；内容预算在 `layouts/budgets.mjs`。

## 演讲可读性 QA（spec：docs/2026-08-24-ppt-readability-qa/spec.md）

1. **内容预算（gate 1，ERROR）**：按版式限制标题字数（两行容量 52 硬限）、正文屏幕字数、单文本块字数、screenPoints（同屏信息点）。source footer 与 notes 不计预算——论证进 notes。
2. **结论—证据一致性（gate 1，ERROR）**：每页可声明 `claim`（缺省=标题）与 `heroEvidence: {kind, factRefs}`（缺省从版式字段推导）；**标题中的数值型 `{{F-x}}` 必须出现在主视觉 factRefs 中**——「标题讲 QPS、主图讲工单」直接 ERROR；非数字结论走关键词重叠软校验（WARN）。
3. **版式语义（gate 1，ERROR）**：上表红线；spec 数组超容量一律 ERROR，builder 不做 slice 静默截断。
4. **投屏可读性（gate 2，ERROR）**：标题 ≤2 行；渲染字号=版式设计字号（禁 shrink-to-fit）；主视觉占正文区 ≥35%；正文文字面积 ≤45%（文字墙）；留白 ≥15%（卡片版式 3%）；卡片 ≤6；关键元素（KPI 数值/请求/ask）字号加粗下限。
5. **视觉复核评分卡（qa.mjs）**：逐页 1–5 分（threeSecond/heroProves/noWall/projectionReady/nextAction），任一维 <4 或非法 → 整 deck FAIL；未复核 → WARN。写入 `<out>/qa-visual-review.json`，复核后重跑 build 生效。

测试：`npm test`（tests/readability.test.mjs，10 失败 + 5 通过 用例）。

## 与 doc-renderer 的边界

- 本目录**不依赖** doc-renderer 的任何代码；doc-renderer 也不依赖这里。
- 共享的只有 `docs/<日期>-<slug>/data/*.json`。
- 网页构建（VitePress）与 PPT 构建（本目录）各自独立运行，gate 各自把守。
