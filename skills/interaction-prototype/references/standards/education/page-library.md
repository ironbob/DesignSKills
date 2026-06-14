# 教育类 App 标准页面库（内置领域标准）

> 用途：作为 interaction-prototype skill 的「页面知识库」。生成教育类 App 的交互原型时，每一个页面都应从本库的标准结构派生，保证产出符合专业交互标准。
>
> 与 `../../epps-schema.md`（Schema 定义）+ `../../validation-rules.md`（校验规则）配套：Schema 定义字段，本库定义该领域有哪些标准页面、长什么样；校验规则引用 Schema 字段。

---

## 一、设计准则（生成时的总纲）

教育类 App 的交互优化目标不是「操作效率」，而是「**促成并维持学习行为**」。所有页面在生成时必须服务以下三个目标之一：

1. **降低开始阻力** —— 让用户用最少决策进入学习。
2. **维持心流** —— 一旦开始，减少打断，密集即时正反馈。
3. **让进度可见** —— 用「已完成」对抗「无尽头」的疲惫。

派生出的 7 条核心标准（详见 `../../validation-rules.md`）：

| # | 标准 | 一句话 |
|---|------|--------|
| 1 | 单一主行动点 | 每页只有一个视觉最强的 primary action |
| 2 | 核心路径极短 | 开 App 到「开始学习」≤ 2 步 |
| 3 | 位置感始终清晰 | 导航 3–5 个 Tab，层级不迷路 |
| 4 | 跳转可预测可逆 | 无死胡同页，有返回 |
| 5 | 关键动作即时反馈 | 做题/完成立即出结果 + 下一步 |
| 6 | 认知负荷可控 | 单页按钮 ≤ 7，信息克制 |
| 7 | 进度成就可见 | 进度、打卡、成就常驻 |

---

## 二、标准页面（6 个核心页面 + 衍生）

每个页面给出：① 定位 → ② 结构分区 → ③ Schema 实例 → ④ 标准跳转 → ⑤ 关键规范 → ⑥ 反模式。

### 页面 1 · 首页 / 学习中心 `home`

**定位**：App 的总入口，核心使命是「**让用户一键继续上次学习**」。

**结构分区（zones，≤4）**：
- 顶部：用户问候 + 今日学习数据（时长/连续打卡）
- 主区：**「继续学习」常驻大卡片**（最高优先级）
- 次区：学习路径/推荐课程
- 底部：Tab Bar

**Schema 实例**：
```yaml
page:
  id: home
  level: 1
  type: home
  primary_action:
    label: "继续学习"
    target: learning_page
    status: "《XX课程》第3章 · 进度65%"
  secondary_actions:
    - { label: "浏览课程", target: course_list, icon: grid }
  navigation: { has_back: false, tab_bar: true }
  progress: { visible: true, elements: [streak, today_minutes] }
  feedback: { type: none, next_action: 进入学习页 }
  density: { button_count: 4, zones: [greeting, continue_card, recommendations, tab_bar] }
  jumps:
    - { trigger: 点击继续学习卡片, from: continue_card, target: learning_page, reversible: true }
    - { trigger: 点击Tab"课程", from: tab_bar, target: course_list, reversible: true }
```

**关键规范**：
- 「继续学习」必须是首屏最大、最显眼的入口（标准 1、2）。
- 状态文案必须带进度，不能是干巴巴的「开始」。
- 首屏不放广告、不放社交动态干扰。

**反模式** ❌：首页堆满课程瀑布流，却没有「继续学习」入口；用户每次都要重新找。

---

### 页面 2 · 课程详情页 `course_detail`

**定位**：决策页——回答用户「这门课学什么、学到哪、现在要不要学」。

**结构分区**：
- 头部：课程封面 + 标题 + 进度条
- 简介：课程目标/适合人群（精简）
- 章节目录：可折叠树状结构，标记已学/未学
- 底部固定栏：**主按钮「继续/开始学习」**

**Schema 实例**：
```yaml
page:
  id: course_detail
  level: 2
  type: course_detail
  primary_action:
    label: "开始学习"            # 有进度时变"继续学习 · 65%"
    target: learning_page
    status: "已完成3/8章"
  secondary_actions:
    - { label: "收藏", target: null, icon: star }
    - { label: "分享", target: null, icon: share }
  navigation: { has_back: true, back_target: course_list, tab_bar: false }
  progress: { visible: true, elements: [overall, chapter_locator] }
  feedback: { type: none, next_action: 进入学习页 }
  density: { button_count: 3, zones: [header, intro, chapters, action_bar] }
  jumps:
    - { trigger: 点击章节, from: chapter_list, target: learning_page, reversible: true }
    - { trigger: 点击主按钮, from: action_bar, target: learning_page, reversible: true }
```

**关键规范**：
- 主按钮在底部固定，不随目录滚动消失。
- 次要操作（收藏/分享）用图标，**绝不可与主按钮等大并排**。
- 章节目录要标记状态（✓已学 / ▶当前 / 未解锁）。

**反模式** ❌：底部 `[试听][收藏][分享][报名]` 四个等大按钮，用户不知该点哪个。

---

### 页面 3 · 学习页 `learning`

**定位**：心流页——学习行为真正发生的核心页面。**信息密度要求最严**。

**结构分区**：
- 顶部：返回 + 章节定位「第3章/共8章」+ 进度
- 主区：内容载体（视频播放器 / 图文 / 音频），占据视觉中心
- 辅助：笔记、字幕、知识点（按需唤起，非默认铺开）
- 底部：上一节 / **完成本节** / 下一节

**Schema 实例**：
```yaml
page:
  id: learning_page
  level: 3
  type: learning
  primary_action:
    label: "完成并继续"
    target: result_page_or_next
    status: "本节即将完成"
  secondary_actions:
    - { label: "笔记", target: note_modal, icon: edit }
    - { label: "目录", target: chapter_drawer, icon: list }
  navigation: { has_back: true, back_target: course_detail, tab_bar: false }
  progress: { visible: true, elements: [chapter_locator, overall] }
  feedback: { type: immediate, next_action: 完成确认→进入下一节/结果页 }
  density: { button_count: 5, zones: [top_bar, content, tools, bottom_bar] }
  jumps:
    - { trigger: 点击"完成并继续", from: bottom_bar, target: result_page, reversible: true }
    - { trigger: 点击目录, from: tools, target: chapter_drawer, reversible: true }
```

**关键规范**：
- 视频学习页**只放**：播放区 + 进度 + 章节切换 + 笔记，**不塞推荐/广告/社交**（标准 6）。
- 进入此页要能从上次断点恢复（「继续观看 05:32」）。
- 完成本节必须有明确的下一步引导，不能停在此页无路可走。

**反模式** ❌：学习页右侧浮窗推荐其他课程、底部弹广告，打断心流。

---

### 页面 4 · 练习 / 测验页 `quiz`

**定位**：反馈密集页——核心是**即时反馈闭环**。

**结构分区**：
- 顶部：进度「3/10」+ 返回
- 主区：**单题聚焦**（一次一题，不铺题海）
- 作答区：选项 / 输入框
- 底部：**提交 →（作答后）显示对错+解析 → 下一题**

**Schema 实例**：
```yaml
page:
  id: quiz_page
  level: 3
  type: quiz
  primary_action:
    label: "下一题"            # 提交后变为"下一题"，二段式
    target: next_question
    status: null
  secondary_actions:
    - { label: "提示", target: hint_modal, icon: bulb }
  navigation: { has_back: true, back_target: course_detail, tab_bar: false }
  progress: { visible: true, elements: [chapter_locator] }
  feedback: { type: immediate, next_action: 提交→对错解析→下一题→最后一题进结果页 }
  density: { button_count: 4, zones: [progress, question, options, action] }
  jumps:
    - { trigger: 完成最后一题, from: action, target: result_page, reversible: true }
```

**关键规范**：
- **一次只显示一题**（标准 6，降低认知负荷）。
- 提交后**立即**显示对错 + 解析（标准 5，immediate 必须满足）。
- 主按钮是二段式：未提交=`提交`，已提交=`下一题`。

**反模式** ❌：一屏铺 5 道题；提交后跳到别处才能看结果（async 反馈）。

---

### 页面 5 · 结果 / 成绩页 `result`

**定位**：闭环页——必须形成「付出→可见成果→下一步」的完整循环。**最易出现死胡同**，重点校验。

**结构分区**：
- 头部：成绩/完成度（环形进度、正确率）
- 成就：连续打卡、解锁徽章
- 概览：错题数、薄弱点
- 底部：**主按钮「继续下一节」+ 次按钮「重做错题」**

**Schema 实例**：
```yaml
page:
  id: result_page
  level: 3
  type: result
  primary_action:
    label: "继续下一节"
    target: learning_page_next
    status: null
  secondary_actions:
    - { label: "重做错题", target: quiz_page_retry, icon: refresh }
    - { label: "返回课程", target: course_detail, icon: back }
  navigation: { has_back: true, back_target: course_detail, tab_bar: false }
  progress: { visible: true, elements: [overall, streak] }
  feedback: { type: immediate, next_action: 继续/重做/返回 三选一 }
  density: { button_count: 3, zones: [score, achievement, summary, action_bar] }
  jumps:
    - { trigger: 点击主按钮, from: action_bar, target: learning_page_next, reversible: true }
    - { trigger: 点击重做错题, from: action_bar, target: quiz_page_retry, reversible: true }
```

**关键规范**：
- **必须有正向出口**（主按钮「继续」），绝不能在成绩页卡死（标准 4，死胡同禁令）。
- 至少给出两个明确下一步选项（继续 / 重做 / 返回）。
- 成就要可见（标准 7，胜任感）。

**反模式** ❌：成绩页只有分数，没有「下一步」按钮，用户只能杀进程。

---

### 页面 6 · 个人中心 `profile`

**定位**：数据与设置页——常驻用户的学习全貌，强化长期成就感。

**结构分区**：
- 头部：头像 + 等级 + 累计学习数据
- 成就区：徽章、连续打卡日历
- 列表：我的课程、错题本、学习统计
- 设置：账户、通知、关于（可折叠）

**Schema 实例**：
```yaml
page:
  id: profile
  level: 1
  type: profile
  primary_action:
    label: "查看学习报告"
    target: stats_page
    status: "本月已学习 28 小时"
  secondary_actions: []
  navigation: { has_back: false, tab_bar: true }
  progress: { visible: true, elements: [overall, streak] }
  feedback: { type: none, next_action: 进入子页 }
  density: { button_count: 5, zones: [header, achievements, lists, settings] }
  jumps:
    - { trigger: 点击"我的课程", from: lists, target: my_courses, reversible: true }
    - { trigger: 点击"错题本", from: lists, target: mistake_book, reversible: true }
```

**关键规范**：
- 作为 level1，必须有 Tab Bar（仅 `scope==whole_app`；`feature_flow` 不会用到 home/profile 这类 level1 页）。
- 数据呈现要服务「胜任感」（累计时长、徽章），不堆砌冷冰冰的设置项。
- 子页面（错题本、学习报告）按 `list` 类型派生。

**反模式** ❌：个人中心只有设置项，看不到学习数据。

---

### 衍生页面

以下页面无独立模板，从已有页面派生：

- `course_list`（课程列表）：从 `profile.lists` 派生，type=`list`。主行动=「进入课程」→ `course_detail`。
- `my_courses`（我的课程）：同上。
- `mistake_book`（错题本）：type=`list`，点击条目→ `quiz_page_retry`。
- `note_modal` / `chapter_drawer` / `hint_modal`：type=`modal`，必须有关闭（reversible）。
- `stats_page`（学习统计）：从 `result` 的成就区扩展，主行动=「返回」。

---

## 三、标准跳转图（页面关系全景）

> 下图适用于 `scope==whole_app`（含底部 Tab、home/profile 等 level1 页）。`scope==feature_flow`（设计 App 内某功能）请见第五节。

```
        ┌─────────────────────────────────────────────┐
        │  Tab Bar (3-5个)                            │
        │  home  /  course_list  /  profile           │
        └──────┬────────────────┬──────────┬──────────┘
               │                │          │
               ▼                ▼          ▼
          [继续学习]      [选课程]     [我的课程/错题本]
               │                │
               └────► course_detail ◄───────┘
                        │  ▲
              [开始/继续]│  │[返回]
                        ▼  │
                  learning_page ────[完成]──► result_page
                        │  ▲                       │
               [目录]   │  │[返回]          [继续]  │[重做]
                        ▼  │                       ▼
                  chapter_drawer              learning_page(下一节)
                        │
        quiz_page ◄─────┴────[练习]
            │
        [最后一题]
            ▼
        result_page
```

**全局跳转规则**：
- 任何跳转必须 `reversible: true`（有返回）。
- 不允许出现「入度=出度=0」的死胡同页。
- `home` 的「继续学习」必须能直达 `learning_page`，是全 App 最短核心路径（home → learning ≤ 2 步）。

---

## 四、使用说明（给生成流程）

1. **生成时**：每个页面必须从本库的某个标准页面派生，填全 EPPS Schema 的所有必填字段。
2. **自检时**：生成后立即用 `../../validation-rules.md` 的规则逐页 + 全局校验。
3. **扩展时**：新页面类型若无法归入现有 6 类，需先在本库登记 Schema，再生成。

---

## 五、`feature_flow` 时如何使用本库

当设计范围是 `scope: feature_flow`（即设计 App 内**某个功能/流程**，如「下单结算」「错题重做流」「发布动态」），**不要**从本库的 `home` / `profile`（level-1 + `tab_bar`）派生——那是整 App 的壳，不属于本功能的范围。改为：

1. **流入口页**用 `level: 2`，从最贴近的二级页派生：
   - 决策/详情类 → 从 `course_detail` 派生（底部固定单一主按钮）。
   - 列表类 → 从 `list` 派生（主行动=进入条目）。
   - 其 `back_target` 指向**入口 host_anchor**（回到宿主 App，如 `host_app_back`），渲染为 `data-host` 提示而非 `go()`。
2. **流内部页**照常派生（`learning` / `quiz` / `result` / `list` / `modal`），`level` 视深度用 2/3，弹窗 `modal`。
3. **流出口**二选一：
   - 指向**出口 host_anchor**（如回到宿主「订单详情」`host_order_detail`）——渲染为 `data-host` 提示。
   - 或 `primary_action.target: null`（行为终结，如「提交订单」）——渲染为 `data-behavior`。
4. **默认 `tab_bar_mode: hidden`**（无 Tab，`.action-bar` 贴底）。仅当该功能本就常驻宿主某 Tab、且需保留 Tab 时，才显式 `tab_bar_mode: inherit` 并补 3–5 个 Tab（此时 R3.1 适用）。

> 一句话：feature_flow 是「一段有入口、有出口的流程」，不是「一个带 Tab 的 App」。host_anchors 是入口/出口，不要把宿主页画进原型。
