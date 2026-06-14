# 交互校验规则表（22 条）

> 配合 interaction-prototype skill 的 Checklist 第 6–7 步。
> 生成页面后，用本表逐页、逐跳转自动校验。每条规则直接引用 `epps-schema.md` 的字段名。两者是**契约关系**。

---

## 一、总则

### 严重级别

| 级别 | 含义 | 处理 |
|------|------|------|
| 🔴 ERROR | 硬性违规，原型不可交付 | 必须修复，阻断 |
| 🟡 WARNING | 质量缺陷，降低体验 | 建议修复，不阻断但扣分 |

### 判定对象

- **页内校验**：针对单个 `page` 对象的字段。
- **跨页校验**：针对整个原型（所有 page 的集合 + 跳转图），需全局视图。

### 质量评分机制

```
合格原型 = 所有 🔴 ERROR 通过  且  WARNING 通过率 ≥ 80%
质量分   = 通过规则数 / 适用规则数 × 100
```

> 适用规则：按页面 `type` 和 `level` 筛选——并非每条规则对每个页面都适用（见每条的「适用」字段）。
>
> 此外还按原型级 `scope` / `tab_bar_mode` 筛选：**R2.1 / R2.2 仅 `scope==whole_app` 适用**（feature_flow 无 home）；**R3.1 仅 `tab_bar_mode==inherit` 适用**（hidden 时无 Tab 集合可数）；**R8.2 仅 `scope==whole_app && level==1` 适用**（feature_flow 无 level-1 页）。`target` / `back_target` / `primary_action.target` 的合法取值集含已声明的 `host_anchor.id`（feature_flow 的外部入口/出口）。
>
> `scripts/validate_epps.py` 还会执行 schema 级门禁（不计入 22 条规则）：`scope_decision` 必填；`feature_flow` 必须声明 `host_anchors` 且禁止 level1；`whole_app` 必须包含 level1 且 `host_anchors` 为空。

### 两层防线：规则（spec 内部）vs 对账（spec↔HTML）

本 22 条**只校验 EPPS spec 自身的内部一致性**（字段完整、跳转闭合、密度合规）——它们看不到 HTML。优先运行 `scripts/validate_epps.py`。**HTML 是否忠实投影了 spec**（zone 多一个/少一个、kind 对不上、示例数据漂移、affordance 双份渲染、modal/page 未投影）由 `scripts/audit_html_projection.py` 兜底：把 HTML 反解析回 zone/action 列表，与 spec 逐项 diff，硬拦截不一致。

> 源头优化（闭环 `zone.kind` 枚举 + 严格投影渲染 + `sample_state` 单一内容源 + `placement` 单点）已让 90% 的 HTML↔spec 漂移**无法产生**；22 条规则守住 spec 质量；对账兜底剩 10%。**规则总数仍固定 22 条**——新增设计场景调「适用」字段或扩 R6.2 判定，不新增规则编号。

---

## 二、校验规则

### 标准 1 · 单一主行动点

#### R1.1 主行动点必须存在且完整 · 🔴 ERROR
- **适用**：所有 `type` 的页面。
- **检查字段**：`primary_action`
- **判定**：`primary_action != null` 且 `primary_action.label` 非空。
- ❌ 失败：`primary_action: null`
- ✅ 通过：`primary_action.label: "继续学习"`

#### R1.2 主行动点应携带状态文案 · 🟡 WARNING
- **适用**：`type ∈ {home, course_detail, profile}`。
- **检查字段**：`primary_action.status`
- **判定**：`status` 非空，且建议包含进度信息（如百分比/章节数/时长）。
- ❌ 失败：详情页 `status: null`（用户不知学到哪）。
- ✅ 通过：`status: "已完成3/8章"`

#### R1.3 次要操作数量受限 · 🔴 ERROR
- **适用**：所有页面。
- **检查字段**：`secondary_actions` 数组长度。
- **判定**：`len(secondary_actions) ≤ 4`。
- ❌ 失败：详情页有 5 个次要操作平铺。

#### R1.4 次要操作不得占据主按钮位置 · 🔴 ERROR
- **适用**：所有页面。
- **检查字段**：`secondary_actions` 与 `primary_action` 是否分离。
- **判定**：`secondary_actions` 必须存在于独立数组中，不得与 `primary_action` 并列同权出现在 `action_bar` 的同级强信号里。（语义约束：不得在底部固定栏生成多个等大主按钮）
- ❌ 失败：底部固定栏出现 4 个等大按钮（试听/收藏/分享/报名）。

---

### 标准 2 · 核心路径极短

#### R2.1 首页必须有一键继续学习入口 · 🔴 ERROR
- **适用**：`scope == whole_app && type == home` 的页面。（`feature_flow` 无 home，本规则不触发。）
- **检查字段**：`primary_action.target`
- **判定**：存在 `level==1 && type==home` 的页，其 `primary_action.target` 指向核心活动页（教育类即 `type==learning`）。
- ❌ 失败：首页主按钮是「浏览课程」而非「继续学习」。

#### R2.2 核心路径步数 ≤ 2 · 🔴 ERROR
- **适用**：`scope == whole_app`（跨页）。（`feature_flow` 无 home→核心 概念；其「入口→完成」由 R4.3 死胡同检测与 host_anchors 出口覆盖。）
- **检查字段**：跳转图最短路径。
- **判定**：从任意 `home` 页到任意核心活动页（`learning`）的跳转链路长度 ≤ 2。
- ❌ 失败：home → course_list → course_detail → learning（3 步，过长）。
- ✅ 通过：home → learning（1 步，直达）。

---

### 标准 3 · 位置感始终清晰

#### R3.1 底部 Tab 数量 3–5 · 🔴 ERROR
- **适用**：`tab_bar_mode == inherit`（即原型确实渲染底部 Tab：`scope==whole_app` 默认 inherit；`scope==feature_flow` 仅当用户要求保留宿主 Tab 时才 inherit）。
- **检查字段**：所有 `navigation.tab_bar == true` 的页面共同决定的 Tab 集合。
- **判定**：`tab_bar_mode == hidden` 时本规则跳过（无 Tab 集合可数）；否则全局 Tab 数量 `3 ≤ N ≤ 5`（米勒定律）。
- ❌ 失败：`inherit` 模式下底部有 7 个 Tab。

#### R3.2 非底层页必须有返回 · 🔴 ERROR
- **适用**：`level != 1` 的所有页面。
- **检查字段**：`navigation.has_back`
- **判定**：`level != 1 ⇒ has_back == true`，且 `back_target` 非空。
- ❌ 失败：`level: 2` 的页面 `has_back: false`。

---

### 标准 4 · 跳转可预测可逆

#### R4.1 所有跳转必须可逆 · 🔴 ERROR
- **适用**：全局（跨页）。
- **检查字段**：`jumps[].reversible`
- **判定**：每一条 jump 的 `reversible == true`。
- ❌ 失败：存在 `reversible: false` 的跳转（不可返回）。

#### R4.2 跳转目标必须存在（无悬空跳转）· 🔴 ERROR
- **适用**：全局（跨页）。
- **检查字段**：`jumps[].target` 与全局已定义的 `page.id` 集合。
- **判定**：每个 `target` 必须等于某个已定义的 `page.id`、或已声明的 `host_anchor.id`、或 schema 白名单内的合法行为标识（如 `next_question`）。
- ❌ 失败：`target: payment_page` 但该页面从未定义。

#### R4.3 禁止死胡同页 · 🔴 ERROR
- **适用**：全局（跨页），排除 `type==modal`。
- **检查字段**：每个 page 的出跳转集合。
- **判定**：除明确终态外，每个页面至少有一个出跳转（`jumps` 非空，或存在 `primary_action.target` 可达）。
- **例外**：`result` 页不算死胡同——因其 `primary_action` 必指向下一步（见 R5.2）。
- ❌ 失败：某成绩页既无主按钮出口、`jumps` 也为空。

#### R4.4 弹窗必须可关闭 · 🔴 ERROR
- **适用**：`type == modal`。
- **检查字段**：`navigation.has_back` 或存在关闭 jump。
- **判定**：`modal` 类型必须提供关闭路径（`has_back: true` 或存在 `reversible: true` 的关闭 jump）。
- ❌ 失败：`note_modal` 无法关闭。

#### R4.5 back_target 必须指向已定义页 · 🔴 ERROR
- **适用**：`navigation.has_back == true` 的页面。
- **检查字段**：`navigation.back_target`
- **判定**：`back_target` 必须等于某个已定义的 `page.id` 或已声明的 `host_anchor.id`（`feature_flow` 流入口页的 back 常指向入口 host_anchor）。无效返回会造成原型坏链，阻断交付。
- ❌ 失败：`back_target: undefined_page`。

---

### 标准 5 · 关键动作即时反馈

#### R5.1 学习/练习页必须即时反馈 · 🔴 ERROR
- **适用**：`type ∈ {quiz, learning}`。
- **检查字段**：`feedback.type`
- **判定**：`feedback.type == "immediate"`。
- ❌ 失败：`quiz_page` 的 `feedback.type: "async"`（做题后跳别处看结果）。

#### R5.2 反馈必须给出下一步 · 🔴 ERROR
- **适用**：`type ∈ {quiz, learning, result}`。
- **检查字段**：`feedback.next_action`
- **判定**：`next_action` 非空，且语义上指向一个明确的后续（下一题/下一节/重做/返回）。
- ❌ 失败：练习完成 `next_action: null`（无路可走）。

---

### 标准 6 · 认知负荷可控

#### R6.1 单页可点元素 ≤ 7 · 🔴 ERROR
- **适用**：所有页面。
- **检查字段**：`density.button_count`
- **判定**：`button_count ≤ 7`（primary + secondary + 其他可点元素）。
- ❌ 失败：某页 `button_count: 12`。

#### R6.2 zones 内容契约良好 · 🔴 ERROR
- **适用**：所有页面。
- **检查字段**：`density.zones`。
- **判定**：① `len(zones) ≤ 4`；② 每个 `zone.kind ∈ 闭环枚举`（见 `epps-schema.md` zone.kind 表，14 种）。枚举外 kind 无法投影，阻断交付。
- ❌ 失败：首页划了 6 个信息区；或 zone 出现枚举外的 kind（如 `study_tip` 未登记）。
- ✅ 通过：3 个区、kind 全在枚举内。
- > 注：本规则是**spec 内部**硬检查（🔴）。HTML 实际渲染的 zone 是否与 spec 声明**一一对应、不多不少**，由 `scripts/audit_html_projection.py` 兜底（硬拦截），不属本 22 条。

---

### 标准 7 · 进度成就可见

#### R7.1 关键页必须显示进度 · 🔴 ERROR
- **适用**：`type ∈ {home, learning, result, profile}`。
- **检查字段**：`progress.visible`
- **判定**：`progress.visible == true`。
- ❌ 失败：`learning` 页不显示任何进度。

#### R7.2 学习页必须有章节定位 · 🟡 WARNING
- **适用**：`type ∈ {learning, quiz, result}`。
- **检查字段**：`progress.elements`
- **判定**：`elements` 至少包含 `chapter_locator` 或 `overall` 之一。
- ❌ 失败：学习页只有「连续打卡」却不知当前第几章。

---

### 全局一致性

#### R8.1 页面 ID 全局唯一 · 🔴 ERROR
- **适用**：全局。
- **检查字段**：所有 `page.id`。
- **判定**：无重复 id。

#### R8.2 底层页必须有 Tab Bar · 🔴 ERROR
- **适用**：`scope == whole_app && level == 1`。（`feature_flow` 无 level-1 页，本规则不触发。）
- **检查字段**：`navigation.tab_bar`
- **判定**：`scope == whole_app && level == 1 ⇒ tab_bar == true`。

#### R8.3 每个 page.id 必须被引用可达 · 🟡 WARNING
- **适用**：全局。
- **检查字段**：`page.id` 是否出现在任意 `jumps[].target` 或 `primary_action.target` 中。
- **判定**：孤立页面（无人指向）应被标记，提示是否为冗余。
- **说明**：`home` 例外，它是起点。

---

## 三、校验执行流程

```
生成交互原型（一组 page 对象 + 跳转图）
        │
        ▼
  ① 逐页校验（页内规则）
     R1.1 R1.2 R1.3 R1.4
     R3.2 R5.1 R5.2 R6.1 R6.2
     R7.1 R7.2 R8.2
        │
        ▼
  ② 全局校验（跨页规则）
     R2.1 R2.2 R3.1
     R4.1 R4.2 R4.3 R4.4 R4.5
     R8.1 R8.3
        │
        ▼
  ③ 运行 scripts/validate_epps.py 汇总：ERROR 全过？WARNING 通过率 ≥ 80%？
        │
        ├─ 是 → 合格，进入 HTML 渲染
        └─ 否 → 列出违规项 → 据此自修复 → 重新校验（循环）
```

---

## 四、规则汇总表

| 规则 | 标准 | 级别 | 核心字段 | 一句话 |
|------|------|------|----------|--------|
| R1.1 | 1 | 🔴 | `primary_action` | 主行动点必须存在 |
| R1.2 | 1 | 🟡 | `primary_action.status` | 主按钮要带状态文案 |
| R1.3 | 1 | 🔴 | `secondary_actions` | 次要操作 ≤ 4 |
| R1.4 | 1 | 🔴 | primary/secondary 分离 | 次要操作不抢占主位 |
| R2.1 | 2 | 🔴 | home.primary_action.target | 首页有一键进入核心活动（仅 `whole_app`） |
| R2.2 | 2 | 🔴 | 跳转图路径 | home→核心活动页 ≤ 2 步（仅 `whole_app`） |
| R3.1 | 3 | 🔴 | Tab 集合 | 底部 Tab 3–5 个（仅 `tab_bar_mode==inherit`） |
| R3.2 | 3 | 🔴 | `navigation.has_back` | 非底层页必有返回 |
| R4.1 | 4 | 🔴 | `jumps[].reversible` | 跳转必须可逆 |
| R4.2 | 4 | 🔴 | `jumps[].target` | 无悬空跳转（`target` 可为 `host_anchor.id`） |
| R4.3 | 4 | 🔴 | 出跳转集合 | 禁止死胡同页 |
| R4.4 | 4 | 🔴 | modal 关闭 | 弹窗必须可关闭 |
| R4.5 | 4 | 🔴 | `back_target` | 返回目标必须存在（可为 `host_anchor.id`） |
| R5.1 | 5 | 🔴 | `feedback.type` | 学习/练习即时反馈 |
| R5.2 | 5 | 🔴 | `feedback.next_action` | 反馈必须给下一步 |
| R6.1 | 6 | 🔴 | `density.button_count` | 单页 ≤ 7 个可点元素 |
| R6.2 | 6 | 🔴 | `density.zones` / `zone.kind` | zones ≤4 且 kind ∈ 枚举（内容契约） |
| R7.1 | 7 | 🔴 | `progress.visible` | 关键页显示进度 |
| R7.2 | 7 | 🟡 | `progress.elements` | 学习页有章节定位 |
| R8.1 | — | 🔴 | `page.id` | ID 全局唯一 |
| R8.2 | — | 🔴 | `navigation.tab_bar` | 底层页有 Tab Bar（仅 `whole_app` & level1） |
| R8.3 | — | 🟡 | 可达性 | 无孤立页面 |

**共 22 条**：🔴 ERROR 18 条（阻断），🟡 WARNING 4 条（扣分）。

> 规则总数固定 22 条。新增设计场景（如 `feature_flow`）通过调整规则的「适用」字段实现，**不新增规则**——以免总数漂移、`SKILL.md` 与本表的「22 条」表述失真。

---

## 五、自修复策略（违规 → 怎么修）

| 违规 | 常见修复手段 |
|------|--------------|
| R1.1 无主行动点 | 给该页补一个最高优先级的 primary（通常是该页核心目的） |
| R1.4 主次按钮等大 | 把次要操作收进图标行，primary 独占底部固定栏 |
| R2.1/R2.2 路径过长 | home 增设直达核心活动页的入口；砍掉中间跳板 |
| R3.1 Tab 过多（仅 `tab_bar_mode==inherit`） | 合并相近 Tab，控制在 3–5；或确认该设计本就不该有 Tab，改 `tab_bar_mode: hidden` |
| R4.1 跳转不可逆 | 给目标页补 `has_back` + `back_target` |
| R4.2 target 悬空 | 补定义该 page / `host_anchor`，或修正 target 到已存在的 page.id / host_anchor.id |
| R4.5 back_target 无效 | 修正为已存在 page.id / host_anchor.id；level1 页不需要 back |
| R4.3 死胡同 | 给该页补 primary 出口或 jump（result 用「继续」） |
| R4.4 modal 无法关 | 补关闭按钮（关闭即 reversible） |
| R5.1 反馈 async | 把结果展示改为同页即时（如 quiz 提交后原地出解析） |
| R6.1 元素过多 | 折叠/收进二级，确保 ≤ 7 |
| R6.2 zone.kind 无效或 zones 过多 | 改为 14 种枚举内 kind；删减/合并到 ≤4 个 zone |
| R7.1 进度缺失 | 补 `progress.visible: true` + 对应元素 |
| 对账·HTML 多出 zone（如「学习提示」） | 二选一：①确实需要 → 在 spec `density.zones` 补声明（kind 取枚举值，如 `hint_block`）；②不需要 → 从 HTML 删除。**不得**留着 spec 没有的区 |
| 对账·示例数据漂移（年级 四 vs 五） | 该值移入 `sample_state`，spec status 与 HTML 统一**插值引用** `{{sample_state.grade}}`，删除各处硬编码 |
| 对账·affordance 双份（卡片内 + 操作栏各一个发音） | 给该 secondary/behavior 定 `placement`（`content` 或 `action_bar` 二选一），HTML 只在选定位置渲染一处 |
| 对账·zone 少渲染 | spec 声明了 zone 但 HTML 漏画 → 按 kind 模板补齐；渲染器不得跳过任何已声明 zone |
| 对账·modal/page 未投影 | 为每个 `type==modal` 增加 `.modal-mask` 或 `<section>`；为每个普通 page 增加对应 `<section id="page.id">` |

> 自修复后**必须重跑校验**，直到合格。修复记录写入 `prototype.md` 的校验报告。
