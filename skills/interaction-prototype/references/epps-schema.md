# EPPS 页面 Schema（Education Prototype Page Schema）

> 配合 interaction-prototype skill 的 Checklist 第 4 步。
> 这是每个页面产出的**结构契约**。字段名与 `validation-rules.md` 完全一致，是校验的唯一锚点。两者是**契约关系**：本文件字段调整，必须同步更新校验规则。

---

## 一、Schema 总览

AI 输出每个页面时，必须按此结构。带「必填」的不可缺省；其余按页面类型决定是否适用（适用性见 `validation-rules.md` 每条规则的「适用」字段）。

```yaml
page:
  id: <snake_case>              # 【必填】唯一标识，如 course_detail
  level: <1|2|3|modal>          # 【必填】1=底层Tab页 2=二级 3=三级 modal=弹窗
  type: <枚举见第三节>           # 【必填】页面类型

  # —— 标准1：单一主行动点 ——
  primary_action:
    label: <文案>               # 【必填】必须有
    target: <page_id | null>     # null 表示触发行为而非跳转，如「提交答案」
    status: <可选状态文案>       # 如「继续学习 · 已完成65%」（home/course_detail/profile 建议）

  # —— 标准6：次要操作降权 ——
  secondary_actions:             # 数组，最多4个，不得与 primary 同权
    - { label, target, icon }

  # —— 标准3 & 4：导航与返回 ——
  navigation:
    has_back: <bool>            # level≠1 时必须 true
    back_target: <page_id>
    tab_bar: <bool>             # 是否显示底部 Tab（仅 level1 为 true）

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
    zones: [<区域名>]           # 页面信息分区，≤4

  # —— 标准4：跳转（必须可逆）——
  jumps:
    - { trigger, from, target, reversible: <bool> }
```

---

## 二、字段语义

| 字段 | 语义 | 约束 |
|------|------|------|
| `id` | 页面唯一标识，全局不可重复 | snake_case；被 `jumps[].target` / `primary_action.target` / `back_target` 引用 |
| `level` | 页面层级，决定导航形态 | `1` 必须有 tab_bar、无 back；`≠1` 必须有 back |
| `type` | 页面类型枚举，决定适用规则 | 见第三节 |
| `primary_action` | 全页视觉最强的单一行动点 | 必须存在且 `label` 非空（R1.1） |
| `primary_action.status` | 主按钮状态文案，承载进度/上下文 | home/course_detail/profile 建议带进度（R1.2） |
| `primary_action.target` | 主按钮跳转目标 | 必须等于某 `page.id`，或为合法行为标识（如 `next_question`） |
| `secondary_actions` | 降权的次要操作（收藏/分享/笔记…） | 数组长度 ≤ 4（R1.3）；不得与 primary 等大并排（R1.4） |
| `navigation.has_back` | 是否有返回 | `level≠1 ⇒ true`（R3.2） |
| `navigation.back_target` | 返回目标 | 必须等于某 `page.id`（R4.5） |
| `navigation.tab_bar` | 是否显示底部 Tab | `level==1 ⇒ true`（R8.2）；全局 Tab 集合 3–5 个（R3.1） |
| `progress.visible` | 是否显示进度 | home/learning/result/profile 必须 true（R7.1） |
| `progress.elements` | 进度元素 | 学习/练习/结果页建议含 chapter_locator 或 overall（R7.2） |
| `feedback.type` | 反馈类型 | quiz/learning 必须 `immediate`（R5.1） |
| `feedback.next_action` | 完成后下一步 | quiz/learning/result 必须非空且语义明确（R5.2） |
| `density.button_count` | 单页可点元素总数 | ≤ 7（R6.1） |
| `density.zones` | 信息分区 | ≤ 4（R6.2） |
| `jumps[].reversible` | 跳转是否可逆 | 每条必须 true（R4.1） |
| `jumps[].target` | 跳转目标 | 必须等于某 `page.id` 或合法行为标识（R4.2） |

---

## 三、页面类型枚举（type）

| type | 含义 | 典型 level | 关键规则提示 |
|------|------|-----------|--------------|
| `home` | 首页 / 学习中心 | 1 | 必须有一键进入核心活动的入口（R2.1）；tab_bar；progress.visible |
| `course_detail` | 详情 / 决策页 | 2 | 底部固定单一主按钮；章节状态标记 |
| `learning` | 学习 / 心流页 | 3 | feedback 必须 immediate；progress.visible；信息密度最严 |
| `quiz` | 练习 / 测验 | 3 | 一次一题；提交后即时对错+解析；主按钮二段式（提交→下一题） |
| `result` | 结果 / 成绩页 | 3 | 必须有正向出口（继续），绝不准死胡同（R4.3） |
| `profile` | 个人中心 | 1 | tab_bar；数据呈现服务胜任感 |
| `list` | 列表页（课程/错题/我的） | 2 | 从已有页面派生，主行动=进入条目 |
| `modal` | 弹窗（笔记/目录/提示） | modal | 必须可关闭（R4.4） |
| `misc` | 其他（统计/设置等） | 视情况 | 无独立模板，按通用标准派生 |

---

## 四、与校验规则的契约

本 Schema 的每个字段都被 `validation-rules.md` 的某条规则锚定：

| Schema 字段 | 锚定规则 |
|-------------|----------|
| `primary_action` | R1.1 R1.2 |
| `secondary_actions` | R1.3 R1.4 |
| `primary_action.target`（home） | R2.1 |
| 跳转图路径 | R2.2 |
| `navigation.tab_bar`（全局） | R3.1 |
| `navigation.has_back` / `back_target` | R3.2 R4.5 |
| `jumps[].reversible` / `target` | R4.1 R4.2 |
| 出跳转集合 | R4.3 |
| `type==modal` 关闭 | R4.4 |
| `feedback.type` / `next_action` | R5.1 R5.2 |
| `density.button_count` / `zones` | R6.1 R6.2 |
| `progress.visible` / `elements` | R7.1 R7.2 |
| `page.id` / `navigation.tab_bar`（level1）/ 可达性 | R8.1 R8.2 R8.3 |

> 若本 Schema 字段调整，必须同步更新 `validation-rules.md` 的判定逻辑。
