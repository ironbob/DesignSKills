# EPPS 页面 Schema（Education Prototype Page Schema）

> 配合 interaction-prototype skill 的 Checklist 第 5 步（逐页 EPPS 设计）。
> 这是每个页面产出的**结构契约**。字段名与 `validation-rules.md` 完全一致，是校验的唯一锚点。两者是**契约关系**：本文件字段调整，必须同步更新校验规则。

---

## 〇、原型级字段（prototype-level，先于单页）

在产出单页之前，先定原型整体的范围与导航形态。这些字段决定哪些校验规则适用（见 `validation-rules.md` 每条规则的「适用」字段）。

```yaml
prototype:
  scope_decision:                    # 【必填】记录为什么选择该范围，防止功能流被误画成整 App
    inferred_from: <user_text | requirement_doc | user_confirmation>
    confidence: <high | medium | low>
    reason: <一句话说明判定依据>
  project_references:                 # 【必填】记录是否参考现有项目文件/代码
    mode: <none | context_only | source_of_truth>
    confirmed_by_user: <bool>
    question: <向用户确认参考源时的问题>
    items:
      - id: <snake_case>
        path: <用户指定路径或输入来源>
        type: <requirement_doc | code | design | prototype | user_prompt | other>
        role: <source_of_truth | context_only | stale_or_conflicting>
        freshness: <current | unknown | stale>
        decision: <adopted | used_for_context | ignored>
        note: <采用/忽略理由；若疑似过时，说明风险>
  scope: <whole_app | feature_flow>   # 【必填】设计目标范围
    # whole_app   = 设计整个 App 主结构，含底部 Tab 与 level1 页
    # feature_flow = 只设计宿主 App 内某个功能/流程；宿主的壳(Tab/level1)不在范围，用 host_anchors 表达入口/出口
  tab_bar_mode: <inherit | hidden>     # 【必填】是否渲染底部 Tab，由 scope 判定后显式写出
    # whole_app   → 默认 inherit（画 Tab）
    # feature_flow → 默认 hidden（不画 Tab）；仅当该功能常驻宿主某 Tab、需保留 Tab 时显式设 inherit
  host_anchors:                        # 【feature_flow 需声明；whole_app 留空】外部入口/出口锚点（非页面）
    - { id: <snake_case>, direction: <entry|exit|both>, label: <语义说明> }

  sample_state:                        # 【必填】单一示例数据源：所有页面的示例值都引用它，不各自硬编码
    grade: <示例年级>                   # 当前年级（如「五年级」）
    unit: <示例单元名>                  # 当前主题/课（如「My Family」）
    today_review_n: <int>              # 今日到期复习数
    today_new_n: <int>                 # 今日新学数
    streak: <int>                      # 连续学习天数
    example_word: { w, ph, gloss, pos, ex }   # 学习/练习/详情页共用的示例学习项
    today_minutes: <int>               # 今日学习分钟数
    course_title: <示例课程名>
    chapter: <示例章节名>
    chapter_total: <int>
    progress_percent: <int>
    # 按需扩展。原则：任何被 ≥2 处用到的示例值，必须落在这里；页面只引用（{{sample_state.grade}}），不重写。
```

> `scope_decision` 是 scope 的审计记录：`confidence: low` 表示用户表达不清。此时必须先问"整 App 还是功能流程？"；若用户仍模糊，按最小影响原则选 `feature_flow`，并把理由写入 `reason`。

> `project_references` 是项目参考源审计记录。读取项目其他文件/代码前必须先问用户；不参考也要写 `mode: none` 与 `confirmed_by_user: true`。未被用户确认的旧代码/旧文档不得标记为 `source_of_truth`。当参考源与当前用户描述冲突时，标记为 `stale_or_conflicting`，并写入未决问题。

> **`sample_state` 是内容的唯一事实源**（S3 源头修复）。`primary_action.status`、进度徽章、示例学习项等，一律从它**插值引用**，禁止在各页 status 字符串或 HTML 里各自硬编码。否则同一数据（如年级）会在 spec 与 HTML、首页与浏览页之间漂移（四年级 vs 五年级就是这么来的）。它不是视觉、不是需求——只是把自审「示例文案要真实可用」形式化成单一来源。

> `host_anchors` 是「世界存在但不在原型内」的目标（如宿主 App 的「购物车」「订单详情」）。它们让 `target`/`back_target`/`primary_action.target` 可以指向原型外部，而不破坏 R4.2/R4.5 的悬空检测——既非 `page.id` 也非已声明 `host_anchor.id` 的值仍判 🔴。**不强制**必须有 anchor：流程原地终结（如「提交订单」`target: null`）合法。

---

## 一、Schema 总览

AI 输出每个页面时，必须按此结构。带「必填」的不可缺省；其余按页面类型决定是否适用（适用性见 `validation-rules.md` 每条规则的「适用」字段）。

```yaml
page:
  id: <snake_case>              # 【必填】唯一标识，如 course_detail
  level: <1|2|3|modal>          # 【必填】1=底层Tab页(仅 scope==whole_app) 2=二级 3=三级 modal=弹窗；scope==feature_flow 禁止 level1，流入口页用 2
  type: <枚举见第三节>           # 【必填】页面类型

  # —— 标准1：单一主行动点 ——
  primary_action:
    label: <文案>               # 【必填】必须有
    target: <page_id | host_anchor_id | legal_behavior | null>  # null 表示触发行为而非跳转，如「提交答案」
    status: <可选状态文案>       # 如「继续学习 · 已完成65%」（home/course_detail/profile 建议）
    element_contract: <见 Element Contract>

  # —— 标准6：次要操作降权 ——
  secondary_actions:             # 数组，最多4个，不得与 primary 同权
    - { label, target, behavior, icon, placement, element_contract }   # placement ∈ {action_bar, content, inline}，默认 action_bar；target 为 null 时填 behavior
  # 行为型 affordance（primary_action 或 secondary 的 target: null，如「发音」「提示」）：
  #   必须且只能在一个 placement 渲染。例：发音要么进 word_card 区(content)，要么进 action_bar，不得两处都画。

  # —— 标准3 & 4：导航与返回 ——
  navigation:
    has_back: <bool>            # level≠1 时必须 true（feature_flow 流入口页 level==2，其 back 指向入口 host_anchor）
    back_target: <page_id | host_anchor_id | null>   # level1 可为 null；level!=1 必须解析到 page/host_anchor
    tab_bar: <bool>             # 是否显示底部 Tab（scope==whole_app 时 level1 必为 true；scope==feature_flow 且 tab_bar_mode==hidden 时全为 false）

  # —— 标准7：进度可见 ——
  progress:
    visible: <bool>
    elements: [<overall | chapter_locator | streak | today_minutes>]

  # —— 标准5：反馈闭环 ——
  feedback:
    type: <immediate | async | none>   # 学习/练习相关页必须 immediate
    next_action: <完成后引导的下一步，如「下一节」>

  # —— 标准6：认知负荷 ——
  density:
    button_count: <int>         # primary + secondary + 其他可点元素总数，≤7
    zones:                      # 内容契约（非计数）：渲染器【只】渲染这里声明的 zone，按序，不多不少
      - { id, kind, label, element_contract }     # kind ∈ 闭环枚举（见第三节）；label 为该区标题，可空；必须声明意图/承载

  # —— 辅助元素：引导/帮助/说明，不进入主内容区 ——
  assistive_elements:
    - { id, kind, label, trigger, target, element_contract }  # guidance/help/tip 类元素放这里，不放 density.zones

  # —— 标准4：跳转（必须可逆）——
  jumps:
    - { trigger, from, target, reversible: <bool> }  # target 必须解析到 page/host_anchor/legal_behavior
```

> 页面**不**直接声明需求覆盖——那是顶层 `page_plan` 的职责（见下「page_plan」）。需求→页面的映射（哪些 P0 落到哪页、聚拢还是拆开、哪些不是页面）集中在 `page_plan` 单一事实源，避免双源漂移。

---

## 一·补、page_plan（需求→页面规划，顶层，与 `pages` 同级）

需求是"能力"单位、不是"页面"单位。`page_plan` 由模型在拆页面时产出，显式回答"每条 P0 落到哪页、是独立页还是某活动的变体形式、哪些需求不是页面"。由 `scripts/validate_page_plan.py`（第三道门）校验。**页面不再用 `satisfies`**——交付关系全部在 `page_plan.delivers`。

```yaml
page_plan:
  pages:
    - page_id: <epps page.id>           # 必须是已定义的 page.id（PLAN.parity）
      kind: standalone | variant        # variant = 某活动的 N 种表现形式之一（如题型）
      variant_of: <组键>                 # kind==variant 时必填；同组多个 variant 即"必须平铺成多页"
      delivers: [<REQ-M##-##>, ...]     # 本页交付的需求 id（非空）；id 来自 extract_requirements
      rationale: <为什么这样聚拢/拆开>   # 必填——把颗粒度判断显式化，供裁判复核
  cross_cutting:                         # 引擎/行为/约束类需求，不建页面
    - req_id: <REQ-M##-##>
      covered_by: <page_id | 引擎/行为说明>
      covered_by_kind: page | engine     # page 时 covered_by 必须是 page.id；engine 由裁判复核
      rationale: <为什么不是页面>
```

- **平铺渲染**：每个 `page_plan.pages[]`（含每个 variant）都必须渲染成独立带 zone 的 `<section>`（`PLAN.flat_render`）——禁止"一页 JS 循环 N variant"。
- **塌缩硬兜底**：聚合需求（"≥N 种"）需 ≥N 个同模块兄弟分散在 ≥N 个不同页面，否则 🔴。
- 颗粒度软规则（`PLAN.granularity.*`，ADVISORY 不阻断）+ LLM 裁判（`references/page-plan-judge.md`）兜底语义。

## 二、字段语义

| 字段 | 语义 | 约束 |
|------|------|------|
| `id` | 页面唯一标识，全局不可重复 | snake_case；被 `jumps[].target` / `primary_action.target` / `back_target` 引用 |
| `level` | 页面层级，决定导航形态 | `1`（仅 `scope==whole_app`）必须有 tab_bar、无 back；`scope==feature_flow` 禁止 level1；`≠1` 必须有 back（流入口页 `level==2`，back 指向入口 host_anchor） |
| `type` | 页面类型枚举，决定适用规则 | 见第三节 |
| `primary_action` | 全页视觉最强的单一行动点 | 必须存在且 `label` 非空（R1.1） |
| `primary_action.status` | 主按钮状态文案，承载进度/上下文 | home/course_detail/profile 建议带进度（R1.2） |
| `primary_action.target` | 主按钮跳转目标 | 必须等于某 `page.id`、已声明 `host_anchor.id`，或为合法行为标识；`null` 表示行为终结（如「提交订单」） |
| `secondary_actions` | 降权的次要操作（收藏/分享/笔记…） | 数组长度 ≤ 4（R1.3）；不得与 primary 等大并排（R1.4） |
| `secondary_actions[].placement` | 该操作渲染在哪 | `action_bar`(默认) / `content`(进某 zone) / `inline`(行内)；一个 affordance 只在一处 |
| `element_contract` | 元素表达意图与承载方式 | 所有 `primary_action`、`secondary_actions[]`、`density.zones[]`、`assistive_elements[]` 必填；见下节 |
| `navigation.has_back` | 是否有返回 | `level≠1 ⇒ true`（R3.2） |
| `navigation.back_target` | 返回目标 | `level!=1` 时必须等于某 `page.id` 或已声明 `host_anchor.id`（R4.5，🔴） |
| `navigation.tab_bar` | 是否显示底部 Tab | `scope==whole_app && level==1 ⇒ true`（R8.2）；`tab_bar_mode==inherit` 时全局 Tab 集合 3–5 个（R3.1） |
| `progress.visible` | 是否显示进度 | home/learning/result/profile 必须 true（R7.1） |
| `progress.elements` | 进度元素 | 学习/练习/结果页建议含 chapter_locator 或 overall（R7.2） |
| `feedback.type` | 反馈类型 | quiz/learning 必须 `immediate`（R5.1） |
| `feedback.next_action` | 完成后下一步 | quiz/learning/result 必须非空且语义明确（R5.2） |
| `density.button_count` | 单页可点元素总数 | ≤ 7（R6.1） |
| `density.zones` | **内容契约**：渲染器只渲染声明的 zone，按序，不多不少 | `len ≤ 4`（R6.2）；每项含 `kind`/`label` |
| `density.zones[].kind` | zone 的渲染模板（闭环） | 必须 ∈ 第三节枚举；否则 R6.2 判 🔴，对账拦截 |
| `assistive_elements` | 辅助/引导/帮助元素 | 引导类元素必须放这里；不得作为主内容 `density.zones[]` 出现 |
| `sample_state` | 原型级示例数据唯一源 | 必填；被 ≥2 处用到的值必须落此；页面引用不硬编码（S3） |
| `jumps[].reversible` | 跳转是否可逆 | 每条必须 true（R4.1） |
| `jumps[].target` | 跳转目标 | 必须等于某 `page.id`、已声明 `host_anchor.id` 或合法行为标识（R4.2） |

### 合法行为标识（legal_behavior）

以下值可作为 `primary_action.target` 或 `jumps[].target` 的非页面行为目标；若渲染为按钮，HTML 用 `data-behavior`，不得误写为 `data-target`：

`next_question` / `previous_question` / `submit_answer` / `retry_quiz` / `play_audio` / `toggle_bookmark` / `share` / `close_modal`

---

## 三、Element Contract：元素意图与承载方式

每个可见元素必须声明 `element_contract`。这不是视觉设计，而是交互契约：说明这个元素为什么存在、应由什么界面承载、主次优先级、出现时机、是否阻断任务流。

```yaml
element_contract:
  intent: <learn_content | primary_action | secondary_action | navigation | status | feedback | guidance | input | error_recovery>
  surface: <main_content | top_bar | action_bar | inline | badge | coachmark | bottom_sheet | modal | toast | menu>
  priority: <primary | secondary | low>
  persistence: <always | contextual | first_time_only | user_invoked | transient>
  blocking: <bool>
```

### intent 闭环枚举

| intent | 含义 | 常见元素 |
|--------|------|----------|
| `learn_content` | 用户要学习/阅读/理解的核心内容 | 词卡、例句、课程内容、章节树 |
| `primary_action` | 当前页最重要的下一步动作 | 继续学习、提交、完成并练习 |
| `secondary_action` | 次要工具或补充操作 | 收藏、分享、发音、笔记、目录 |
| `navigation` | 位置与返回/切换 | back、tab、目录跳转 |
| `status` | 进度、状态、成就、计数 | streak、掌握度、进度条 |
| `feedback` | 成功/失败/对错/下一步反馈 | 答题解析、toast、结果提示 |
| `guidance` | 引导、帮助、学习方法说明 | 新手引导、提示、学习方法 |
| `input` | 输入、选择、作答 | 选项、填空、听写输入 |
| `error_recovery` | 纠错、重试、恢复 | 重做错题、重新提交 |

### surface 闭环枚举

| surface | 含义 |
|---------|------|
| `main_content` | 主内容区，只承载核心学习/题目/列表/结果内容 |
| `top_bar` | 顶部栏 |
| `action_bar` | 底部主操作/工具栏 |
| `inline` | 行内轻量元素 |
| `badge` | 徽章/状态 |
| `coachmark` | 首次引导浮层 |
| `bottom_sheet` | 用户唤起的底部说明面板 |
| `modal` | 阻断式弹窗/独立辅助页 |
| `toast` | 短暂反馈 |
| `menu` | 更多菜单 |

### 意图-承载矩阵（硬规则）

| intent | 允许 surface | 关键约束 |
|--------|--------------|----------|
| `learn_content` | `main_content` | 可作为主内容；通常 `priority: primary/secondary`、`persistence: always/contextual` |
| `primary_action` | `action_bar` | 每页最多一个 `priority: primary` |
| `secondary_action` | `action_bar` / `inline` / `menu` | 不得抢占 primary |
| `navigation` | `top_bar` / `menu` / `action_bar` | 返回、Tab、目录入口 |
| `status` | `badge` / `top_bar` / `inline` | 不作为大块主内容 |
| `feedback` | `inline` / `toast` / `bottom_sheet` | quiz/learning 反馈应即时 |
| `guidance` | `coachmark` / `bottom_sheet` / `inline` / `modal` | **禁止 `main_content`**；默认 `priority: low`、`blocking: false` |
| `input` | `main_content` / `inline` | 题目/表单可以主区承载 |
| `error_recovery` | `action_bar` / `bottom_sheet` / `inline` | 重试/恢复类动作 |

> 稳定生成要求：不要让 AI "凭感觉"决定表现形式；先填 `intent`，再从允许的 `surface` 中选择。`validate_epps.py` 会阻断缺字段、枚举外、以及如 `intent: guidance` + `surface: main_content` 的冲突。

---

## 四、页面类型枚举（type）

| type | 含义 | 典型 level | 关键规则提示 |
|------|------|-----------|--------------|
| `home` | 首页 / 学习中心 | 1 | 仅 `scope==whole_app`；必须有一键进入核心活动的入口（R2.1）；tab_bar；progress.visible |
| `course_detail` | 详情 / 决策页 | 2 | 底部固定单一主按钮；章节状态标记 |
| `learning` | 学习 / 心流页 | 3 | feedback 必须 immediate；progress.visible；信息密度最严 |
| `quiz` | 练习 / 测验 | 3 | 一次一题；提交后即时对错+解析；主按钮二段式（提交→下一题） |
| `result` | 结果 / 成绩页 | 3 | 必须有正向出口（继续），绝不准死胡同（R4.3） |
| `profile` | 个人中心 | 1 | 仅 `scope==whole_app`；tab_bar；数据呈现服务胜任感 |
| `list` | 列表页（课程/错题/我的） | 2 | 从已有页面派生，主行动=进入条目 |
| `modal` | 弹窗（笔记/目录/提示） | modal | 必须可关闭（R4.4） |
| `misc` | 其他（统计/设置等） | 视情况 | 无独立模板，按通用标准派生 |

---

### zone.kind 闭环枚举（渲染投影契约）

`density.zones[].kind` 只能取下表值。**渲染器只能为已声明的 zone、按其 kind 取对应模板渲染**——不渲染任何未声明的 zone（堵住「学习提示」凭空多出主内容区的口子，S1/S2 源头修复）。若元素意图是 `guidance`，应进 `assistive_elements` 而不是 `density.zones`。新增 kind 必须先在本表登记 + 在 `html-render-template.md` 配模板，否则 R6.2 与渲染对账双双拦截。

| kind | 渲染为 | 典型 type | 可点？ |
|------|--------|-----------|--------|
| `hero_card` | 渐变大卡（今日/继续学习） | home/course_detail | 是（→ primary target） |
| `quick_entries` | 图标快捷入口行 | home/course_detail | 是（→ 各 target） |
| `badge_strip` | 进度徽章行（streak/今日/定位） | home/learning/result | 否 |
| `word_card` | 学习项卡（词头+音标+词性+释义+例句） | learning/modal | 含 affordance |
| `option_list` | 题干 + 选项 | quiz | 是（选） |
| `input_block` | 文本输入作答区 | quiz | 是（输入） |
| `row_list` | 可点列表行（→ 详情/进入） | list/course_detail | 是（→ target） |
| `chapter_tree` | 分层树（年级/主题/课 + 状态标记） | list/course_detail | 是（→ target） |
| `mastery_bar` | 掌握度分布条 | course_detail/result | 否 |
| `score_ring` | 环形成绩 | result | 否 |
| `stat_grid` | 统计数字网格 | misc/profile | 否 |
| `progress_strip` | 完成度进度条 | course_detail/misc | 否 |
| `hint_block` | 提示/说明文本块（非可点） | learning/quiz/misc | 否 |
| `text_block` | 通用说明/占位文本 | misc | 否 |

> 14 种。是**闭环**：HTML 里出现的每一个主内容区，都必须能对回某条 `zone.kind`；引导/帮助/提示类元素必须对回 `assistive_elements[]`。对不上的即漂移，对账拦截。

---

## 五、与校验规则的契约

本 Schema 的每个字段都被 `validation-rules.md` 的某条规则锚定：

| Schema 字段 | 锚定规则 |
|-------------|----------|
| `primary_action` | R1.1 R1.2 |
| `secondary_actions` | R1.3 R1.4 |
| `primary_action.target`（home） | R2.1（仅 `scope==whole_app`） |
| 跳转图路径 | R2.2（仅 `scope==whole_app`） |
| `navigation.tab_bar`（全局） | R3.1（仅 `tab_bar_mode==inherit`） |
| `navigation.has_back` / `back_target` | R3.2 R4.5（`back_target` 可指向 `host_anchor.id`） |
| `jumps[].reversible` / `target` | R4.1 R4.2（`target` 可指向 `host_anchor.id`） |
| 出跳转集合 | R4.3 |
| `type==modal` 关闭 | R4.4 |
| `feedback.type` / `next_action` | R5.1 R5.2 |
| `density.button_count` / `zones` / `zones[].kind` | R6.1 R6.2（枚举外 kind 为 🔴） |
| `sample_state` / `placement` / `element_contract` / HTML zone 投影 | 自审对账 + schema 规则（见 `SKILL.md` 第 9 步与 `html-render-template.md` §五） |
| `progress.visible` / `elements` | R7.1 R7.2 |
| `page.id` / `navigation.tab_bar`（level1）/ 可达性 | R8.1 R8.2（仅 `scope==whole_app`） R8.3 |
| `page_plan`（需求→页面规划，顶层） | 外部 PLAN 门禁 `validate_page_plan.py`（**非 22 条之一**；P0 未交付/未平铺渲染即阻断） |

> 若本 Schema 字段调整，必须同步更新 `validation-rules.md` 的判定逻辑。
> **`zone.kind` 枚举（14 种）、`placement` 取值（3 种）、`element_contract` 枚举与意图-承载矩阵是跨文件契约**：本表 + `html-render-template.md` 投影表 + `validation-rules.md` + `validate_epps.py` + `standards/education/page-library.md` 实例，改一处必同步其余处。
