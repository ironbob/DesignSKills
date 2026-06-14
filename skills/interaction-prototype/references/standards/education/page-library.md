# 教育类移动 App 标准页面库

> 用途：作为 interaction-prototype skill 的页面知识库。生成教育/学习类移动 App 原型时，每个页面都从本库派生，再按 `../../epps-schema.md` 填全字段，并用 `../../validation-rules.md` 与脚本校验。

---

## 一、教育类交互目标

教育类 App 的交互优化目标不是单纯缩短操作，而是**促成并维持学习行为**：

1. **降低开始阻力**：打开后能快速继续学习。
2. **维持心流**：学习中减少打断，练习中即时反馈。
3. **让进度可见**：用完成度、章节定位、连续学习强化胜任感。

派生出的 7 条标准：

| # | 标准 | 一句话 |
|---|------|--------|
| 1 | 单一主行动点 | 每页只有一个视觉最强的 primary action |
| 2 | 核心路径极短 | 开 App 到开始学习 ≤ 2 步 |
| 3 | 位置感始终清晰 | Tab 3–5 个，层级不迷路 |
| 4 | 跳转可预测可逆 | 无悬空 target、无坏返回、无死胡同 |
| 5 | 关键动作即时反馈 | 学习/练习完成后立即给结果与下一步 |
| 6 | 认知负荷可控 | 单页按钮 ≤ 7，zones ≤ 4 且 kind 可投影 |
| 7 | 进度成就可见 | 关键页显示章节/整体进度 |

---

## 二、标准页面类型

| type | 作用 | 派生要点 |
|------|------|----------|
| `home` | 学习中心 | level1；primary 直达 `learning`；显示 streak/today_minutes |
| `list` | 课程/错题/我的课程列表 | level2；列表项跳详情或练习 |
| `course_detail` | 决策页 | level2；底部固定主按钮；章节树显示状态 |
| `learning` | 学习心流页 | level3；即时反馈；章节定位；工具降权 |
| `quiz` | 练习页 | level3；一次一题；提交后即时解析 |
| `result` | 结果页 | level3；必须有正向出口 |
| `profile` | 个人中心 | level1；学习数据与报告入口 |
| `modal` | 笔记/目录/提示 | level modal；必须可关闭 |
| `misc` | 统计/设置等 | 按通用标准派生 |

---

## 三、完整闭合 EPPS 样例

以下样例故意保持最小但完整：所有 target 都能解析，所有示例值都引用 `sample_state`，所有 zone.kind 都在闭环枚举内。生成新原型时可复制结构，但必须替换为当前需求。

```json epps
{
  "prototype": {
    "scope_decision": {
      "inferred_from": "user_confirmation",
      "confidence": "high",
      "reason": "样例展示完整学习 App 主结构，包含首页、课程、学习、练习、结果和个人中心"
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
      "score_percent": 80,
      "example_word": {
        "w": "parents",
        "ph": "/ˈpeərənts/",
        "gloss": "父母",
        "pos": "n.",
        "ex": "My parents love me very much."
      }
    }
  },
  "pages": [
    {
      "id": "home",
      "level": 1,
      "type": "home",
      "primary_action": {
        "label": "继续学习",
        "target": "learning_page",
        "status": "{{sample_state.course_title}} · {{sample_state.chapter}} · {{sample_state.progress_percent}}%"
      },
      "secondary_actions": [
        {"label": "浏览课程", "target": "course_list", "behavior": null, "icon": "grid", "placement": "content"}
      ],
      "navigation": {"has_back": false, "back_target": null, "tab_bar": true},
      "progress": {"visible": true, "elements": ["streak", "today_minutes"]},
      "feedback": {"type": "none", "next_action": "进入学习页"},
      "density": {
        "button_count": 4,
        "zones": [
          {"id": "today_status", "kind": "badge_strip", "label": "今日"},
          {"id": "continue_learning", "kind": "hero_card", "label": "继续学习"},
          {"id": "quick_entries", "kind": "quick_entries", "label": "快捷入口"}
        ]
      },
      "jumps": [
        {"trigger": "点击继续学习卡片", "from": "continue_learning", "target": "learning_page", "reversible": true},
        {"trigger": "点击课程 Tab", "from": "tab_course", "target": "course_list", "reversible": true},
        {"trigger": "点击我的 Tab", "from": "tab_profile", "target": "profile", "reversible": true}
      ]
    },
    {
      "id": "course_list",
      "level": 2,
      "type": "list",
      "primary_action": {"label": "进入课程", "target": "course_detail", "status": null},
      "secondary_actions": [],
      "navigation": {"has_back": true, "back_target": "home", "tab_bar": false},
      "progress": {"visible": false, "elements": []},
      "feedback": {"type": "none", "next_action": "进入课程详情"},
      "density": {"button_count": 2, "zones": [{"id": "courses", "kind": "row_list", "label": "课程"}]},
      "jumps": [{"trigger": "点击课程行", "from": "courses", "target": "course_detail", "reversible": true}]
    },
    {
      "id": "course_detail",
      "level": 2,
      "type": "course_detail",
      "primary_action": {
        "label": "继续学习",
        "target": "learning_page",
        "status": "{{sample_state.chapter}}/{{sample_state.chapter_total}} · {{sample_state.progress_percent}}%"
      },
      "secondary_actions": [
        {"label": "收藏", "target": null, "behavior": "toggle_bookmark", "icon": "star", "placement": "action_bar"},
        {"label": "分享", "target": null, "behavior": "share", "icon": "share", "placement": "action_bar"}
      ],
      "navigation": {"has_back": true, "back_target": "course_list", "tab_bar": false},
      "progress": {"visible": true, "elements": ["overall", "chapter_locator"]},
      "feedback": {"type": "none", "next_action": "进入学习页"},
      "density": {
        "button_count": 4,
        "zones": [
          {"id": "course_progress", "kind": "progress_strip", "label": "进度"},
          {"id": "chapters", "kind": "chapter_tree", "label": "章节"}
        ]
      },
      "jumps": [
        {"trigger": "点击章节", "from": "chapters", "target": "learning_page", "reversible": true},
        {"trigger": "点击主按钮", "from": "action_bar", "target": "learning_page", "reversible": true}
      ]
    },
    {
      "id": "learning_page",
      "level": 3,
      "type": "learning",
      "primary_action": {"label": "完成并练习", "target": "quiz_page", "status": "{{sample_state.example_word.w}}"},
      "secondary_actions": [
        {"label": "笔记", "target": "note_modal", "behavior": null, "icon": "edit", "placement": "action_bar"},
        {"label": "目录", "target": "chapter_drawer", "behavior": null, "icon": "list", "placement": "action_bar"},
        {"label": "发音", "target": null, "behavior": "play_audio", "icon": "volume", "placement": "content"}
      ],
      "navigation": {"has_back": true, "back_target": "course_detail", "tab_bar": false},
      "progress": {"visible": true, "elements": ["chapter_locator", "overall"]},
      "feedback": {"type": "immediate", "next_action": "完成后进入练习页"},
      "density": {
        "button_count": 5,
        "zones": [
          {"id": "word", "kind": "word_card", "label": "学习项"},
          {"id": "hint", "kind": "hint_block", "label": "提示"}
        ]
      },
      "jumps": [
        {"trigger": "点击完成并练习", "from": "action_bar", "target": "quiz_page", "reversible": true},
        {"trigger": "点击笔记", "from": "tools", "target": "note_modal", "reversible": true},
        {"trigger": "点击目录", "from": "tools", "target": "chapter_drawer", "reversible": true}
      ]
    },
    {
      "id": "quiz_page",
      "level": 3,
      "type": "quiz",
      "primary_action": {"label": "提交", "target": "next_question", "status": null},
      "secondary_actions": [
        {"label": "提示", "target": "hint_modal", "behavior": null, "icon": "bulb", "placement": "action_bar"}
      ],
      "navigation": {"has_back": true, "back_target": "learning_page", "tab_bar": false},
      "progress": {"visible": true, "elements": ["chapter_locator"]},
      "feedback": {"type": "immediate", "next_action": "提交后显示解析；最后一题进入结果页"},
      "density": {"button_count": 5, "zones": [{"id": "question", "kind": "option_list", "label": "练习题"}]},
      "jumps": [
        {"trigger": "完成最后一题", "from": "action_bar", "target": "result_page", "reversible": true},
        {"trigger": "点击提示", "from": "tools", "target": "hint_modal", "reversible": true}
      ]
    },
    {
      "id": "result_page",
      "level": 3,
      "type": "result",
      "primary_action": {"label": "继续下一节", "target": "learning_page", "status": null},
      "secondary_actions": [
        {"label": "重做错题", "target": "quiz_page", "behavior": null, "icon": "refresh", "placement": "action_bar"},
        {"label": "返回课程", "target": "course_detail", "behavior": null, "icon": "back", "placement": "action_bar"}
      ],
      "navigation": {"has_back": true, "back_target": "quiz_page", "tab_bar": false},
      "progress": {"visible": true, "elements": ["overall", "streak"]},
      "feedback": {"type": "immediate", "next_action": "继续下一节或重做错题"},
      "density": {
        "button_count": 3,
        "zones": [
          {"id": "score", "kind": "score_ring", "label": "成绩"},
          {"id": "mastery", "kind": "mastery_bar", "label": "掌握情况"}
        ]
      },
      "jumps": [
        {"trigger": "点击继续下一节", "from": "action_bar", "target": "learning_page", "reversible": true},
        {"trigger": "点击重做错题", "from": "action_bar", "target": "quiz_page", "reversible": true}
      ]
    },
    {
      "id": "profile",
      "level": 1,
      "type": "profile",
      "primary_action": {"label": "查看学习报告", "target": "stats_page", "status": "{{sample_state.today_minutes}} 分钟 · 连续 {{sample_state.streak}} 天"},
      "secondary_actions": [],
      "navigation": {"has_back": false, "back_target": null, "tab_bar": true},
      "progress": {"visible": true, "elements": ["overall", "streak"]},
      "feedback": {"type": "none", "next_action": "进入学习统计"},
      "density": {"button_count": 4, "zones": [{"id": "stats", "kind": "stat_grid", "label": "统计"}, {"id": "links", "kind": "row_list", "label": "入口"}]},
      "jumps": [
        {"trigger": "点击学习报告", "from": "primary", "target": "stats_page", "reversible": true},
        {"trigger": "点击首页 Tab", "from": "tab_home", "target": "home", "reversible": true},
        {"trigger": "点击课程 Tab", "from": "tab_course", "target": "course_list", "reversible": true}
      ]
    },
    {
      "id": "stats_page",
      "level": 2,
      "type": "misc",
      "primary_action": {"label": "返回我的", "target": "profile", "status": null},
      "secondary_actions": [],
      "navigation": {"has_back": true, "back_target": "profile", "tab_bar": false},
      "progress": {"visible": false, "elements": []},
      "feedback": {"type": "none", "next_action": "返回个人中心"},
      "density": {"button_count": 1, "zones": [{"id": "report", "kind": "stat_grid", "label": "学习报告"}]},
      "jumps": [{"trigger": "点击返回我的", "from": "action_bar", "target": "profile", "reversible": true}]
    },
    {
      "id": "note_modal",
      "level": "modal",
      "type": "modal",
      "primary_action": {"label": "关闭", "target": "close_modal", "status": null},
      "secondary_actions": [],
      "navigation": {"has_back": true, "back_target": "learning_page", "tab_bar": false},
      "progress": {"visible": false, "elements": []},
      "feedback": {"type": "none", "next_action": "回到学习页"},
      "density": {"button_count": 1, "zones": [{"id": "note_body", "kind": "text_block", "label": "笔记"}]},
      "jumps": [{"trigger": "点击关闭", "from": "modal", "target": "learning_page", "reversible": true}]
    },
    {
      "id": "chapter_drawer",
      "level": "modal",
      "type": "modal",
      "primary_action": {"label": "关闭", "target": "close_modal", "status": null},
      "secondary_actions": [],
      "navigation": {"has_back": true, "back_target": "learning_page", "tab_bar": false},
      "progress": {"visible": false, "elements": []},
      "feedback": {"type": "none", "next_action": "回到学习页"},
      "density": {"button_count": 2, "zones": [{"id": "chapter_list", "kind": "chapter_tree", "label": "目录"}]},
      "jumps": [{"trigger": "点击章节", "from": "chapter_list", "target": "learning_page", "reversible": true}]
    },
    {
      "id": "hint_modal",
      "level": "modal",
      "type": "modal",
      "primary_action": {"label": "关闭", "target": "close_modal", "status": null},
      "secondary_actions": [],
      "navigation": {"has_back": true, "back_target": "quiz_page", "tab_bar": false},
      "progress": {"visible": false, "elements": []},
      "feedback": {"type": "none", "next_action": "回到练习页"},
      "density": {"button_count": 1, "zones": [{"id": "hint_text", "kind": "hint_block", "label": "提示"}]},
      "jumps": [{"trigger": "点击关闭", "from": "modal", "target": "quiz_page", "reversible": true}]
    }
  ]
}
```

---

## 四、`feature_flow` 时如何使用本库

当设计范围是 `scope: feature_flow`（只设计宿主 App 内某个学习流程，如「错题重做流」），不要派生 `home` / `profile` 这类 level1 壳页面。改为：

1. 流入口页用 `level: 2`，从 `list` 或 `course_detail` 派生。
2. 入口页的 `navigation.back_target` 指向入口 `host_anchor.id`。
3. 流出口指向出口 `host_anchor.id`，或用 `primary_action.target: null` 表示行为终结。
4. 默认 `tab_bar_mode: hidden`；只有用户明确要求保留宿主 Tab，才设 `inherit` 并补齐 3–5 个 Tab。

一句话：`feature_flow` 是一段有入口、有出口的学习流程，不要把宿主 App 的壳画进原型。
