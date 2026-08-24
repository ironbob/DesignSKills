# ppt-renderer 演讲可读性 QA 规范（v1.0）

- 日期：2026-08-24
- 状态：**已实施**（落点：`layouts/budgets.mjs` 预算契约、各 layout `FONT_SPEC/HERO_NAMES/KEY_ELEMENTS`、`layouts/roadmap.mjs`、`check-storyboard.mjs` 三检查、`check-slides.mjs` `checkProjection`、`checks/qa.mjs` `applyVisualReview`、`tests/readability.test.mjs` 15 例全绿）
- 范围：在现有三道 gate（`check-storyboard` 数据层 / `check-slides` 几何层 / `render-png` 像素层）+ `qa.mjs` 汇总之上，补充五类质量门禁：内容预算、结论—证据一致性、版式语义、投屏可读性、视觉复核评分卡。
- 现有覆盖（不重复设计）：元素重叠、越界、字号下限、折行估算；图表数值与 facts.json 一致；PNG/PDF 渲染成功。

## 0. 设计原则

1. **数据层能判的不过几何层**：字数、条数、字段组合、claim—证据引用关系，全部在 `check-storyboard`（构建前拦截，省一次构建）；几何/字号/占比/反 shrink 在 `check-slides`；像素与感知分别在 `render-png` 和视觉复核。
2. **预算超限 = ERROR**：现有 `DENSITY_LIMIT`（perSlide 320 / perBlock 130，WARN）废弃，替换为按版式的 ERROR 预算表（§2.1）。
3. **禁静默截断**：现有 `requests.slice(0,3)`、`kpis.slice(0,4)`、`pairs.slice(0,2)` 这类截断改为「spec 超量 → ERROR」，防止内容在 builder 里被悄悄丢掉绕过预算。
4. **机器 proxy 判确定性，感知判断进评分卡**：「三秒读出结论」无法确定性判定——机器 gate 管可测代理（字号/占比/行数/引用一致），最终感知由 1–5 评分卡把守，任一维 <4 整 deck FAIL。

背景佐证：金标准 `docs/2026-08-23-h1-backend-review/data/h1-backend-2026.storyboard.json` 第 5 页存在真实错位——标题「{{F-7}} 零降级零资损：**{{F-17}} 峰值 QPS** 背后是三道防线」，主图 `factValues` 只有 **F-19（对账工单）**。§2 结论—证据一致性规则有真实靶子。

---

## 1. 推荐的数据字段

### 1.1 storyboard 每页新增（两个字段，均可推导、声明用于交叉校验）

```jsonc
{
  "no": 5,
  "layout": "conclusion-chart",
  "title": "{{F-7}} 零降级零资损：{{F-17}} 峰值 QPS 背后是三道防线",

  // 新增①：一句话结论（≤30 字）。缺省 = title。
  // 用途：视觉复核「三秒能否读出结论」的评分锚点；不新增硬 gate（「标题即结论」已由中性标题规则把守）
  "claim": "618 峰值 5,200 QPS 零资损，靠的是三道防线",

  // 新增②：主视觉声明（证据页必填；title 版式豁免）
  // kind 必须等于该版式的主视觉类型；factRefs 必须与从版式字段推导出的集合一致（防声明漂移）
  "heroEvidence": {
    "kind": "chart",                  // chart | flow | kpi | pairs | requests | roadmap | none
    "factRefs": ["F-19.baseline", "F-19"]
  }
}
```

`factRefs` 推导规则（checker 内置，声明缺省时自动推导）：

| layout | 主视觉 kind | factRefs 推导来源 |
|---|---|---|
| title | none | 豁免 |
| exec-summary | kpi | `kpis[].value` 的插值引用 |
| conclusion-chart | chart | `chart.metrics[].baselineFact/currentFact` + `series/segments[].factValues` |
| mechanism | flow | `evidence` + `flow.rows[].steps[]` 的插值引用 |
| risk-action | pairs | `pairs[].risk.evidence` 的插值引用 |
| decision-ask | requests | `requests[].target/baseline` 的插值引用 |
| roadmap（新增版式） | roadmap | `workstreams[].milestone` 的插值引用 |

### 1.2 roadmap 版式契约（新增，与 decision-ask 分家）

```jsonc
{
  "layout": "roadmap",
  "title": "H2 三条规划：方法论复制到履约域与资金链路",
  "workstreams": [                       // ≤3 项
    { "what": "履约域微服务化推广", "milestone": "2026-12-15 前首阶段拆分", "owner": "本人" }
  ],
  "linkNote": "三条线均从 H1 沉淀长出",    // 可选，≤30 字
  "source": "…", "notes": { … }
}
```

**禁入字段**：`target / baseline / resources / requests / askLine`——资源申请是决策语义，属 `decision-ask`；roadmap 只承载「做什么·里程碑·谁」。

### 1.3 视觉复核产物（机器可读，与现有 `qa-visual-review.md` 并行）

`<out>/qa-visual-review.json`：

```jsonc
{
  "reviewer": "ai | human",
  "slides": [
    { "no": 1, "threeSecond": 5, "heroProves": 5, "noWall": 5,
      "projectionReady": 5, "nextAction": 4, "note": "..." }
  ]
}
```

### 1.4 版式字号注册（反 shrink-to-fit 的依据）

每个 layout 导出 `FONT_SPEC`：元素名前缀 → 声明字号（即 `tokens.mjs TYPE` 的落点），如 `'cc-takeaway': 12.5`、`'da-what': 14`、`'es-thesis': 14.5`。`check-slides` 据此断言「渲染字号 = 设计字号」。

---

## 2. 阈值表

### 2.1 内容预算（check-storyboard，全部 ERROR；字数=解析插值后的中文字符，`source`/`notes.*`/`tag`/页码不计）

| layout | 标题字数 | 正文屏幕字数 | 单文本块上限 | screenPoints 上限 | 单块细则 |
|---|---|---|---|---|---|
| title | ≤ 24 | ≤ 130 | subtitle 42；meta 每行 28 | 4 | meta ≤3 行 |
| exec-summary | ≤ 30 | ≤ 260 | thesis 48；risk 30；ask 36；kpi label 12 | 8（thesis1+risks2+ask1+kpi4） | kpis 恰 ≤4；risks ≤2 |
| conclusion-chart | ≤ 30 | ≤ 180 | takeaway 60 | 3（chart1+takeaway2） | takeaways ≤2，禁右侧长段落 |
| mechanism | ≤ 30 | ≤ 190 | step label 10；sub 14；evidence 45；linkNote 30 | 11（steps ≤10 + evidence1） | rows ≤3；每行 steps ≤4 |
| risk-action | ≤ 30 | ≤ 220 | risk.what 20；evidence 55；action.what 20；detail 40 | 4（2 对×2 侧） | pairs ≤2 |
| decision-ask | ≤ 30 | ≤ 240 | what 28；target 32；baseline 32；resources 28；owner 16 | 3（requests2+askband1） | **requests ≤2**（三卡紧凑模式废除） |
| roadmap | ≤ 30 | ≤ 200 | what 24；milestone 28；owner 16 | 3 | workstreams ≤3；禁 target/baseline/resources |

通用：标题 > 52 字（≈23pt 两行容量）ERROR；28–52 WARN（鼓励一行）。阈值来源：各文本框几何容量 ×80% 反推（如 takeaway 框 2.9in×0.92in @12.5pt ≈ 容量 68 字 → 预算 60）。

### 2.2 版式语义组合规则（check-storyboard，ERROR）

| 规则 | 判定 |
|---|---|
| exec-summary 四模块并存的条件 | thesis、risks、kpis、ask 四者**同时**存在时，thesis 必须 ≤48 字；超限 → ERROR「长 thesis 不得与风险列表+四 KPI+ask 同屏，二选一：压缩 thesis 或拆页」 |
| decision-ask 请求数 | `requests.length > 2` → ERROR「最多两项请求，第三项移 roadmap 或附录」 |
| roadmap 字段禁令 | 任一 workstream 含 `target/baseline/resources`，或页含 `requests/askLine` → ERROR「资源申请字段属 decision-ask」 |
| conclusion-chart 右栏 | `takeaways.length > 2` 或任条 >60 字 → ERROR「右栏最多两条辅助说明，禁止长段落」 |
| 静默截断禁令 | spec 数组长度 > 版式容量（kpis>4、pairs>2、steps>4/行、takeaways>2、requests>2、workstreams>3）→ ERROR，不允许 builder slice 吞掉 |

### 2.3 投屏可读性（check-slides 几何代理 + render-png 像素复核，ERROR）

| 指标 | 阈值 | 判定层 |
|---|---|---|
| 标题行数 | estLines(title, 23pt, ~9in) ≤ 2 | check-slides |
| 渲染字号=设计字号 | 任一元素 `fontSize < FONT_SPEC[前缀] − 0.5pt` → ERROR（shrink-to-fit 禁令） | check-slides |
| 主视觉占比 | hero 元素组面积 / 正文区(9.0×3.48in) ≥ 35% | check-slides |
| 文字面积占比 | Σ min(estTextH, h)×w（除 title/source/pageno/tag）/ 正文区 ≤ 45%（>40% WARN） | check-slides |
| 留白比例 | 1 − (文字 ink + panel 面积)/正文区 ≥ 15% | check-slides |
| 卡片数量 | panel/card 元素 ≤ 6/页 | check-slides |
| 缩略图关键元素 | KPI 数值/主图高亮标注 ≥20pt；askband/请求 what ≥12pt 且 bold+accent 对比 | check-slides；感知确认交评分卡 |

### 2.4 视觉复核评分卡（1–5 分锚点）

| 维度 | 5 分 | 3 分 | 1 分 |
|---|---|---|---|
| threeSecond 三秒读出结论 | 标题即唯一结论，扫一眼即得 | 需读两块以上才拼出结论 | 无结论/中性标题 |
| heroProves 主视觉证明结论 | 主图直接承载标题数字/关系 | 相关但不支撑关键事实 | 错位（标题 QPS、主图工单） |
| noWall 无文字墙 | 正文在预算内、信息组 ≤3 | 一块逼近上限 | 段落/文字墙 |
| projectionReady 适合投屏 | 6 米外可读、对比度足 | 需凑近/局部过小 | 缩略图不可辨 |
| nextAction 下一步明确 | 该页明确推进决策/含行动 | 方向可 infer | 无推进（title/章首页按叙事位豁免下限 4） |

**门禁**：任一维缺失、非法（非 1–5 整数）或 <4 → 该页 ERROR → 整 deck FAIL。

---

## 3. check-storyboard 与 check-slides 职责划分

| 检查 | check-storyboard（构建前，sb+facts+已解析文本） | check-slides（构建后，几何模型+解析产物） |
|---|---|---|
| 内容预算 | ✅ 标题/正文/单块字数、screenPoints 计数（spec 结构即可判） | —（沿用折行估算作兜底） |
| 结论—证据一致性 | ✅ heroEvidence 声明 vs 推导一致；标题数值引用 ⊆ hero factRefs；关键词重叠软校验(WARN) | — |
| 版式语义 | ✅ 模块组合规则、条数上限、roadmap 字段禁令、静默截断禁令 | — |
| 投屏可读性 | 标题字数（52 上限） | ✅ 标题 ≤2 行、反 shrink 字号断言、hero 占比、文字面积/留白/卡片数、缩略图关键元素字号 |
| 视觉复核 | — | —（属 `qa.mjs`：读 `qa-visual-review.json`，任一维 <4 → ERROR；缺失 → 沿用现有占位提示 + WARN） |
| 既有不变 | schema/中性标题/决策闭环/裸数字/插值可解析 | 重叠/越界/折行/占位符/图表数字=facts |

`render-png` 可选扩展：正文区像素 ink 占比与几何估算交叉验证（>5% 偏差 WARN，提示几何模型失真）。

---

## 4. 伪代码

```text
# ── check-storyboard 新增 ──────────────────────────────

BUDGET = 按 §2.1 表加载；EXCLUDE_FIELDS = {source, pageno, tag, notes.*}

function checkContentBudget(sb, resolved):
  for sl in resolved.slides:
    b = BUDGET[sl.layout]
    if cjkCount(sl.title) > b.titleChars: ERROR `${tag} 标题 ${n} 字超预算 ${b.titleChars}`
    bodyChars = Σ cjkCount(f) for 每个内容字段 f ∈ sl，排除 EXCLUDE_FIELDS
    if bodyChars > b.slideChars: ERROR `${tag} 正文 ${n} 字超预算（论证进 notes）`
    for (字段, 上限) in b.blockLimits:
      if cjkCount(值) > 上限: ERROR `${tag} ${字段} 单块超限`
    pts = screenPoints(sl)
    if pts > b.points: ERROR `${tag} 同屏信息点 ${pts} > ${b.points}`

function screenPoints(sl):           # 同屏信息点 = 观众需逐个消化的语义单元
  switch sl.layout:
    title:            1(subtitle) + meta行数
    exec-summary:     1(thesis) + risks.n + 1(ask) + kpis.n
    conclusion-chart: 1(chart) + takeaways.n
    mechanism:        Σ row.steps.n + 1(evidence)
    risk-action:      pairs.n × 2
    decision-ask:     requests.n + 1(askband)
    roadmap:          workstreams.n

function checkClaimHero(sb, facts, resolved):
  for sl in resolved.slides where sl.layout != 'title':
    derived = deriveHeroFactRefs(sl)            # §1.1 表
    hero = sl.heroEvidence ?? { kind: layoutHeroKind(sl.layout), factRefs: derived }
    if hero.kind != layoutHeroKind(sl.layout): ERROR `${tag} heroEvidence.kind 与版式主视觉不符`
    if set(hero.factRefs) != set(derived): ERROR `${tag} heroEvidence.factRefs 与实际主视觉漂移`
    titleRefs = 数值型插值引用(resolve(sl.title))   # 携带 value/deltaDisplay 的 {{F-x}}；日期/期间白名单沿用
    missing = titleRefs − hero.factRefs
    if missing: ERROR `${tag} 标题关键事实 ${missing} 未由主视觉直接表达（标题讲A、主图讲B）`
    if keywordOverlap(sl.title, heroLabels(sl)) < 0.34: WARN `${tag} 标题与主视觉关键词重叠低（非数字结论建议自查）`

function checkLayoutSemantics(sb):
  for sl in sb.slides:
    if sl.layout == 'exec-summary' and 全部四模块(thesis, risks, kpis, ask)
       and cjkCount(sl.thesis) > 48:
      ERROR `${tag} 长 thesis 与风险+四KPI+ask 同屏——压缩 thesis 或拆页`
    if sl.layout == 'decision-ask' and sl.requests.length > 2:
      ERROR `${tag} 请求 ${n} 项 > 2——第三项移 roadmap/附录`
    if sl.layout == 'roadmap' and (含 requests/askLine 或 workstream 含 target/baseline/resources):
      ERROR `${tag} roadmap 不得承载资源申请字段（属 decision-ask）`
    if sl.layout == 'conclusion-chart' and (sl.takeaways.length > 2):
      ERROR `${tag} 辅助说明 > 2 条`
    for (数组, 容量) in [(kpis,4),(pairs,2),(takeaways,2),(requests,2),(workstreams,3),(row.steps,4)]:
      if 数组.length > 容量: ERROR `${tag} ${数组} 超容量 ${容量}——不允许 builder 静默截断`

# ── check-slides 新增 ──────────────────────────────────

BODY = { x:0.5, y:1.42, w:9.0, h:3.48 }        # tokens.mjs GRID

function checkProjection(page, layout):
  title = page.elements.find(name ∈ {title, cover-title})
  if Placer.estLines(title.text, title.fontSize, title.w) > 2: ERROR `${tag} 标题超两行`
  for el in page.elements where el.kind == 'text':
    declared = layout.FONT_SPEC[前缀(el.name)]     # 版式字号注册
    if declared and el.fontSize < declared - 0.5:
      ERROR `${tag} ${el.name} 渲染字号 ${el.fontSize} < 设计 ${declared}（shrink-to-fit 禁令）`
  hero = page.elements.filter(name ∈ layout.HERO_NAMES)
  if area(hero) / area(BODY) < 0.35: ERROR `${tag} 主视觉占比 ${pct} < 35%`
  ink = Σ min(Placer.estTextH(el), el.h) × el.w for 文本 el，排除 title/source/pageno/tag
  if ink / area(BODY) > 0.45: ERROR `${tag} 正文文字面积 ${pct} > 45%（文字墙）`
  if 1 − (ink + panelArea) / area(BODY) < 0.15: ERROR `${tag} 留白不足 15%`
  if count(panel/card) > 6: ERROR `${tag} 卡片 ${n} > 6`
  for el in page.elements where el.name ∈ 关键元素注册:   # kpi-value / chart 标注 / da-what / askband
    if not (el.fontSize ≥ 20 or (el.fontSize ≥ 12 and el.bold and el.onAccent)):
      ERROR `${tag} 关键元素 ${el.name} 缩略图不可识别`

# ── qa.mjs 新增（视觉复核 gate）────────────────────────

function applyVisualReview(outDir):
  vr = readJSON(`${outDir}/qa-visual-review.json`)
  if !vr: return { errs: [], warns: ['视觉复核未完成——交付前逐页查看 png/ 并写评分卡'] }
  errs = []
  for s in vr.slides:
    for dim in [threeSecond, heroProves, noWall, projectionReady, nextAction]:
      if not isIntInRange(s[dim], 1, 5): errs.push(`slide ${s.no}: ${dim} 评分非法`)
      elif s[dim] < 4: errs.push(`slide ${s.no}: ${dim}=${s[dim]} < 4`)
  return { errs, warns: [] }     # 任一 ERROR → 整 deck verdict=FAIL（复核后重跑 build 拼回判定）
```

---

## 5. 测试用例（10 失败 + 5 通过）

字段引用沿用金标准 facts（F-10 P99、F-17 峰值 QPS、F-19 工单、F-27 上手周期）。

### 应失败

| # | 输入摘要 | 预期 |
|---|---|---|
| F01 | conclusion-chart，`takeaways` 3 条（金标准第 3/5/6 页现状） | storyboard ERROR：辅助说明 >2 条 |
| F02 | conclusion-chart，标题含 `{{F-17}}` 峰值 QPS，`chart.factValues=[F-19.baseline, F-19]`（金标准第 5 页现状） | storyboard ERROR：标题关键事实 F-17 未由主视觉表达 |
| F03 | decision-ask，`requests` 3 项全字段 | storyboard ERROR：请求 >2 项（同时废 compact 三卡分支） |
| F04 | exec-summary，thesis 96 字 + risks 2 + kpis 4 + ask（四模块并存） | storyboard ERROR：长 thesis 不得与风险+四 KPI+ask 同屏 |
| F05 | 任意版式，title 58 字 | storyboard ERROR：标题 >52 字（两行容量）；几何层 estLines=3 亦 ERROR |
| F06 | conclusion-chart，builder 因塞不下把 takeaway 渲染为 10.5pt（设计 12.5pt） | check-slides ERROR：渲染字号 < 设计−0.5（shrink-to-fit 禁令） |
| F07 | conclusion-chart，单条 takeaway 92 字（金标准第 5 页防线三条现状） | storyboard ERROR：单块 >60 字，右栏禁长段落 |
| F08 | conclusion-chart，图表框缩至 3.2×2.4in（占比 22%），右侧文字扩栏 | check-slides ERROR：主视觉占比 <35% |
| F09 | roadmap，workstream 含 `target/baseline/resources` 完整字段 | storyboard ERROR：资源申请字段属 decision-ask |
| F10 | 全部机器 gate 通过；`qa-visual-review.json` 第 5 页 `threeSecond: 2` | qa 汇总 ERROR → 整 deck FAIL（复核后重跑 build 生效） |

### 应通过

| # | 输入摘要 | 预期 |
|---|---|---|
| P01 | conclusion-chart：标题引 F-10/F-11，metricsBar 同 refs，takeaways 2×≤60 字 | 全 gate PASS |
| P02 | decision-ask：2 项 requests 全闭环字段（what/target/baseline/resources/owner/deadline）+ askLine 40 字 | PASS |
| P03 | exec-summary：thesis 44 字 + risks 2×30 + kpis 4 + ask 35 字（四模块并存但 thesis 短） | PASS |
| P04 | mechanism：2 行 × 3 步（label ≤10、sub ≤14）+ evidence 42 字 | PASS（screenPoints 7 ≤ 11） |
| P05 | roadmap：3 条 workstreams（what/milestone/owner），无资源字段，linkNote 28 字 | PASS |

---

## 6. 对现有金标准的影响（迁移提示）

- `h1-backend-2026` 会挂 **F01 / F02 / F03 / F04 / F07 五处**——第 5 页的 QPS/工单错位是真实缺陷应修；takeaways 3→2、requests 3→2（第三条移 roadmap）、thesis 压缩属于新标准的既定收紧，需回填精简或在 calibrate 时显式记录豁免。
- `decision-ask.mjs` 的 `compact` 三卡分支、`check-slides.mjs` 的 `slice(0,3)` 类静默截断是本规范点名要废除的「绕过通道」，实施时一并处理。
- 视觉复核 gate 沿用现有「复核后重跑 build 自动拼回」机制，只加 `.json` 评分卡的机器判定。
