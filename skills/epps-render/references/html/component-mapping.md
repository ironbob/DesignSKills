# HTML 组件映射：14 zone.kind → HTML

> 用途：把 EPPS 的 14 种 `density.zones[].kind` 映射到 HTML 结构 + CSS class，并定义主次层级样式。与 `render-template.md`、`projection.manifest.yaml`、上游 `epps-schema.md` 的 zone.kind 枚举（14 种，闭合）同进同退。
> 14 种必须全覆盖；新增 kind 必须先在上游 `epps-schema.md` 登记，再在此补映射。

---

## 一、zone.kind → HTML 结构

| kind | HTML 结构（class） | 内容来源 | 可点？ |
|------|--------------------|----------|--------|
| `hero_card` | `.zone.hero`（渐变大卡，标题 + 副线 + primary 入口） | `primary_action` + `sample_state` | 是（→ primary target） |
| `quick_entries` | `.quick-row > .quick`（图标快捷入口行） | `secondary_actions` 或显式入口 | 是（→ 各 target） |
| `badge_strip` | `.zone.badge-row > .badge`（进度徽章行） | `progress.elements` + `sample_state` | 否 |
| `word_card` | `.zone`（`.word-head` 词头 + `.ph` 音标 + `.pos` 词性 + `.gloss` 释义 + `.ex` 例句） | `sample_state.example_word` | 含 affordance（发音） |
| `option_list` | `.zone`（`.q-stem` 题干 + `.opts > .opt` 选项 + `.feedback-panel` 即时反馈） | 题干、选项、反馈 | 是（选） |
| `input_block` | `.zone`（`.text-in` 输入框 + `.feedback-panel`） | 输入题 | 是（输入） |
| `row_list` | `.zone`（`.row` 可点列表行） | 列表项 | 是（→ target） |
| `chapter_tree` | `.zone`（`.tree-item` 分层缩进项 + 状态标记） | 章节/状态 | 是（→ target） |
| `mastery_bar` | `.zone`（`.mastery` 堆叠掌握度条） | 掌握度统计 | 否 |
| `score_ring` | `.zone`（`.score-ring` 环形成绩） | 成绩百分比 | 否 |
| `stat_grid` | `.zone`（`.stat-grid` 统计数字网格） | 统计值 | 否 |
| `progress_strip` | `.zone`（`.bar-track` 完成度进度条） | 完成度百分比 | 否 |
| `hint_block` | `.zone.placeholder`（提示文本块） | 提示文案 | 否 |
| `text_block` | `.zone.placeholder`（通用文本） | 文本 | 否 |

> 每个 zone 容器必须带 `data-zone-id` + `data-zone-kind`（投影标记，见 `render-template.md`）。

---

## 二、主次层级 → HTML 样式（核心：主次分明）

层级由 **`element_contract.priority`** 决定，映射到按钮 class：

| 权重 | 来源 | HTML class | 样式要点 |
|------|------|-----------|----------|
| `primary` | `primary_action` | `.btn-primary` | 满宽（`width:100%`）、`background:var(--primary)` 填充、`color:var(--onPrimary)`、`font-weight:600`、`border-radius:var(--shape-medium)`；唯一 |
| `secondary` | `secondary_actions[]`（`placement: action_bar`） | `.btn-sec`（放 `.sec-row`，在 primary 之上） | 描边（`1px solid var(--outline)`）、`background:surface`、`color:var(--onSurface)`、较小内边距；降权 |
| `secondary`（inline） | `placement: content`/`inline` | 行内图标按钮 `.icon-btn` | 小尺寸图标，不抢占 primary |
| `low` | 辅助/引导 | 不渲染为主行动点 | 用 `.placeholder`/`.badge` 等弱表达 |

**硬约束**：
- 每页**只有一个** `.btn-primary`（标记即 class `btn-primary`；对账 `PRIMARY.unique` 计数 ≤ 1）。
- `.sec-row` 放在 `.btn-primary` 之上；primary 始终最宽、最强。
- 行为型 affordance（`target==null`，如发音/提示）按 `placement` **只在一处**渲染。

---

## 三、zone 内容优先级 → 视觉权重

| zone `element_contract.priority` | 视觉表达 |
|----------------------------------|----------|
| `primary`（如 `hero_card`/`word_card`） | 大卡、渐变/强调背景、大字号 |
| `secondary`（如 `progress_strip`/`mastery_bar`） | 普通卡片、收敛尺寸 |
| `low`（如 `hint_block`） | `.placeholder` 弱化、`onSurfaceVariant` 色 |

---

## 四、element_contract.surface → HTML 承载

| surface | HTML 承载 |
|---------|-----------|
| `main_content` | `.zone[data-zone-id][data-zone-kind]` |
| `top_bar` | `.topbar` |
| `action_bar` | `.action-bar` |
| `badge` | `.badge` |
| `inline` | 行内按钮/`.inline-help` |
| `coachmark` | `.coachmark[data-assistive-id][data-assistive-kind]` |
| `bottom_sheet` | `.sheet[data-assistive-id][data-assistive-kind]` |
| `modal` | `.screen.modal-mask#<id>` |
| `toast` | `.toast` |
| `menu` | `.menu`/`.drawer` |

> `intent: guidance` 禁止用 `.zone` 承载；用 coachmark / bottom sheet / inline help / modal。
