# 输出格式：prototype.md + EPPS 顶层结构

> 配合 Checklist 第 8 步。交付目录必须同时包含 `prototype.md`、`prototype.html`。建议额外保存 `epps.json`，方便脚本稳定校验。

---

## 一、交付目录

```text
prototype/YYYY-MM-DD-<主题>/
├── prototype.md
├── prototype.html
└── epps.json              # 推荐：与 prototype.md 中的 EPPS 块完全一致
```

---

## 二、`prototype.md` 固定模板

````markdown
# 交互原型：<主题>

## 需求摘要

- 核心用户：
- 使用场景：
- 关键路径：
- 范围：`whole_app` / `feature_flow`
- 范围判定依据：整 App / 功能流程的触发词、用户确认或需求文档依据
- 项目参考源：不参考 / 仅上下文 / 当前事实源；列出用户允许读取的路径

## 参考源清单

| id | path/input | type | role | freshness | decision | note |
|----|------------|------|------|-----------|----------|------|

> 未经用户确认的项目旧代码/旧文档不得作为 `source_of_truth`。冲突或疑似过时内容写入未决问题。

## 页面清单

| page.id | type | level | 角色 |
|---------|------|-------|------|

## EPPS 规范

```json epps
{
  "prototype": {
    "scope_decision": {
      "inferred_from": "user_confirmation",
      "confidence": "high",
      "reason": "用户明确要求设计整个学习 App 的主结构"
    },
    "project_references": {
      "mode": "none",
      "confirmed_by_user": true,
      "question": "是否需要参考已有项目文件或代码？",
      "items": []
    },
    "scope": "whole_app",
    "tab_bar_mode": "inherit",
    "host_anchors": [],
    "sample_state": {
      "grade": "五年级",
      "unit": "My Family",
      "today_review_n": 8,
      "today_new_n": 10,
      "streak": 12,
      "today_minutes": 18,
      "course_title": "英语核心词汇",
      "chapter": "第3章",
      "chapter_total": 8,
      "progress_percent": 65,
      "example_word": {
        "w": "parents",
        "ph": "/ˈpeərənts/",
        "gloss": "父母",
        "pos": "n.",
        "ex": "My parents love me very much."
      }
    }
  },
  "pages": []
}
```

## 跳转图

用文本或 Mermaid 表达所有 page / host_anchor 的正向路径与返回路径。

## 校验报告

运行：

```bash
python skills/interaction-prototype/scripts/validate_epps.py prototype/YYYY-MM-DD-<主题>/prototype.md
python skills/interaction-prototype/scripts/audit_html_projection.py prototype/YYYY-MM-DD-<主题>/prototype.md prototype/YYYY-MM-DD-<主题>/prototype.html
python skills/interaction-prototype/scripts/validate_page_plan.py prototype/YYYY-MM-DD-<主题>/prototype.md <需求文档.md> prototype/YYYY-MM-DD-<主题>/prototype.html
```

> 第三道门之前先起草 `page_plan` 并跑 **LLM 裁判 critique**（建议性，见 `references/page-plan-judge.md`）：检查有无塌缩的交互模式 / 过度拆分的共现内容 / 误分类的 cross_cutting，据发现修 `page_plan`，再跑上面的 `validate_page_plan.py`（唯一硬门禁）。

记录 ERROR/WARNING 结果、质量分、修复记录。

## 未决问题

只记录交互范围外或需求待确认事项。
````

---

## 三、EPPS 顶层 JSON/YAML Schema

```yaml
prototype:
  scope_decision:                              # required
    inferred_from: user_text | requirement_doc | user_confirmation
    confidence: high | medium | low
    reason: string
  project_references:                           # required
    mode: none | context_only | source_of_truth
    confirmed_by_user: boolean
    question: string
    items:
      - id: snake_case
        path: string                           # file path, doc path, or input label
        type: requirement_doc | code | design | prototype | user_prompt | other
        role: source_of_truth | context_only | stale_or_conflicting
        freshness: current | unknown | stale
        decision: adopted | used_for_context | ignored
        note: string
  scope: whole_app | feature_flow              # required
  tab_bar_mode: inherit | hidden               # required after scope is confirmed
  host_anchors:                                # required for feature_flow, [] for whole_app
    - id: host_learning_center
      direction: entry | exit | both
      label: 宿主 App 的入口/出口说明
  sample_state:                                # required
    grade: string
    unit: string
    today_review_n: integer
    today_new_n: integer
    streak: integer
    today_minutes: integer
    course_title: string
    chapter: string
    chapter_total: integer
    progress_percent: integer
    score_percent: integer                      # result 页 score_ring 引用；无结果页可省略
    example_word:
      w: string
      ph: string
      gloss: string
      pos: string
      ex: string

pages:
  - id: snake_case                             # required, unique
    level: 1 | 2 | 3 | modal                   # required
    type: home | course_detail | learning | quiz | result | profile | list | modal | misc
    primary_action:
      label: string
      target: page_id | host_anchor_id | legal_behavior | null
      status: string | null
      element_contract:
        intent: primary_action
        surface: action_bar
        priority: primary
        persistence: contextual
        blocking: false
    secondary_actions:
      - label: string
        target: page_id | host_anchor_id | legal_behavior | null
        behavior: string | null                # required when target is null and rendered as behavior
        icon: string
        placement: action_bar | content | inline
        element_contract:
          intent: secondary_action
          surface: action_bar | inline | menu
          priority: secondary | low
          persistence: contextual | user_invoked
          blocking: false
    navigation:
      has_back: boolean
      back_target: page_id | host_anchor_id | null
      tab_bar: boolean
    progress:
      visible: boolean
      elements: [overall | chapter_locator | streak | today_minutes]
    feedback:
      type: immediate | async | none
      next_action: string | null
    density:
      button_count: integer
      zones:
        - id: snake_case
          kind: hero_card | quick_entries | badge_strip | word_card | option_list | input_block | row_list | chapter_tree | mastery_bar | score_ring | stat_grid | progress_strip | hint_block | text_block
          label: string
          element_contract:
            intent: learn_content | status | input | feedback
            surface: main_content | badge | inline
            priority: primary | secondary | low
            persistence: always | contextual
            blocking: false
    assistive_elements:
      - id: snake_case
        kind: hint_block | text_block | chapter_tree
        label: string
        trigger: first_enter | user_tap | contextual
        target: page_id | host_anchor_id | legal_behavior | null
        element_contract:
          intent: guidance
          surface: coachmark | bottom_sheet | inline | modal
          priority: low
          persistence: first_time_only | user_invoked | contextual
          blocking: false
    jumps:
      - trigger: string
        from: string
        target: page_id | host_anchor_id | legal_behavior
        reversible: true

page_plan:                                    # 顶层，与 pages 同级；需求→页面规划（第三道门）
  pages:
    - page_id: quiz_fill                       # 必须是上面 pages[].id
      kind: variant                            # standalone | variant
      variant_of: quiz                         # variant 必填
      delivers: [REQ-M03-01]                   # 交付的需求 id（extract_requirements 抽取）
      rationale: 填空是独立交互形式
  cross_cutting:                              # 引擎/行为/约束类，不建页面
    - req_id: REQ-M04-01
      covered_by: review_queue
      covered_by_kind: engine                  # page | engine
      rationale: SM-2 是调度引擎，由复习队列承载
```

---

## 四、HTML 投影标记要求

为让 `scripts/audit_html_projection.py` 能机械化对账，`prototype.html` 必须保留以下属性：

- 每屏：`<section class="screen" id="<page.id>" data-level="<level>" data-type="<type>" data-tabbar="true|false">`
- 每个内容区：`<div class="zone" data-zone-id="<zone.id>" data-zone-kind="<zone.kind>">`
- 每个辅助元素：`data-assistive-id="<assistive.id>" data-assistive-kind="<assistive.kind>"`
- 页面内跳转：`data-target="<page.id>"`
- 宿主入口/出口：`data-host="<host_anchor.id>" data-host-label="<host_anchor.label>"`
- 行为动作：`data-behavior="<behavior>"`

HTML 可有中性样式，但不得删除这些投影标记。
