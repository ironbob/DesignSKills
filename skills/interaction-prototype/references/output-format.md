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
```

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
    secondary_actions:
      - label: string
        target: page_id | host_anchor_id | legal_behavior | null
        behavior: string | null                # required when target is null and rendered as behavior
        icon: string
        placement: action_bar | content | inline
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
    jumps:
      - trigger: string
        from: string
        target: page_id | host_anchor_id | legal_behavior
        reversible: true
```

---

## 四、HTML 投影标记要求

为让 `scripts/audit_html_projection.py` 能机械化对账，`prototype.html` 必须保留以下属性：

- 每屏：`<section class="screen" id="<page.id>" data-level="<level>" data-type="<type>" data-tabbar="true|false">`
- 每个内容区：`<div class="zone" data-zone-id="<zone.id>" data-zone-kind="<zone.kind>">`
- 页面内跳转：`data-target="<page.id>"`
- 宿主入口/出口：`data-host="<host_anchor.id>" data-host-label="<host_anchor.label>"`
- 行为动作：`data-behavior="<behavior>"`

HTML 可有中性样式，但不得删除这些投影标记。
