# outline.json 契约（机器源 / 下游交接物）

> 这是 `book-talk-planner` 的**唯一事实源**：结构化选题提纲。`scripts/validate_outline.py` 校验它（完整性/覆盖），`outline.md` 是它的渲染，`validate_contract.py` 对账防漂移。
> **下游 skill（生成口播逐字稿）直接消费这份 JSON**——字段稳定、无歧义。

## 一、顶层结构

```json
{
  "meta": { ... },          // 书的元信息 + 可讲性判断
  "topics": [ { ... }, ... ] // 3-8 个选题点
}
```

## 二、meta 字段

| 字段 | 必填 | 取值 / 类型 | 说明 |
|------|------|-------------|------|
| `book` | ✅ | string | 书名 |
| `author` | — | string | 作者（不确定可空串） |
| `input_mode` | ✅ | `title_only` / `title_plus_summary` / `full_text` | 书的内容怎么进来的（决定可信度松紧） |
| `user_angle_direction` | ✅ | string | 用户是否有想讲的角度/思路："无" 或 具体思路内容 |
| `tone` | ✅ | string | 目标调性，默认 `深度+通俗平衡` |
| `knowledge_source` | ✅ | object | 知识来源声明（见下）：内容从哪来、是否核对原文 |
| `selectability` | ✅ | object | 可讲性判断（见下） |

### selectability（可讲性）
| 字段 | 必填 | 取值 | 说明 |
|------|------|------|------|
| `verdict` | ✅ | `worth_telling` / `marginal` / `thin` | 这本书值不值得讲 |
| `talkable_points_estimate` | ✅ | int | 预估可讲点数量级 |
| `form` | ✅ | `series` / `single` | 适合做成系列还是单条 |
| `viral_potential` | ✅ | `high` / `medium` / `low` | 整体爆款潜力 |
| `viral_reason` | ✅ | string | 潜力判据（一句话） |

### knowledge_source（知识来源）—— 必填
声明本提纲的知识来源与核对状态，让下游 skill / 读者知道内容从哪来、能信几分。**门 `O-SOURCE` 硬卡 declaration 非空**——尤其 `title_only`（凭记忆）时必须显式声明"未核对原文"。

| 字段 | 必填 | 取值 | 说明 |
|------|------|------|------|
| `declaration` | ✅ | string | 一句话声明内容来源 + 核对状态。按 input_mode 写：`title_only`→"基于 LLM 对本书的训练记忆生成，未逐条核对原文；具体论断/年代/数字/史例在成稿前需核实出处"；`title_plus_summary`→"基于用户提供的摘要 + LLM 知识"；`full_text`→"基于导入的全书原文《<文件名/版本>》生成" |
| `edition` | — | string | 可选：版本/译者/出版社（讲书要 attributable 到具体版本时填，否则空串） |

## 三、topics[] 字段（每个选题点 = 一个可讲主题）

| 字段 | 必填 | 取值 / 类型 | 规则 |
|------|------|-------------|------|
| `id` | ✅ | `T\d+`（如 `T01`） | 全局唯一、递增 |
| `title` | ✅ | string | 选题主题（**选题粒度，非章节名**） |
| `angle` | ✅ | angle-library 里的 id | 必须存在于 `angle-library.md`（门 `O-ANGLE` 硬卡） |
| `angle_name` | ✅ | string | 视角中文名（与库一致） |
| `hook_directions` | ✅ | string[]，**1-2 条** | 开头钩子方向（不写成品句，指方向即可） |
| `key_points` | ✅ | string[]，**3-5 条** | 核心讲解要点 |
| `golden_line_direction` | ✅ | string | 金句/记忆点方向 |
| `video_form` | ✅ | `single` / `series` | 适合形态（single=1-3 分钟单条） |
| `why_worth_telling` | ✅ | string | 为什么值得讲（爆款/共鸣理由） |
| `credibility` | ✅* | object[] | 涉史实/经济/数据论断时**必填**（见下）；无可信度敏感论断可空数组 |
| `title_directions` | ✅(P1) | string[]，**2-3 条** | 标题方向（钩子型） |
| `cover_direction` | ✅(P1) | string | 封面文案方向 |

> `credibility` 的 `*`：只要 key_points / hook 里出现具体历史年代、人物、经济数据、因果判断，就必须在 `credibility` 里逐条列出并标 level。宁可多标。

### credibility[] 条目
| 字段 | 必填 | 取值 | 说明 |
|------|------|------|------|
| `claim` | ✅ | string | 被标注的论断 |
| `level` | ✅ | `credible` / `uncertain` / `unverified` | 可信 / 存疑 / 待核实 |
| `reason` | ✅ | string | 判据（如"全书原文有据"/"凭记忆，需核实出处"） |

**输入风险联动（门 `O-CRED`）**：`input_mode == title_only`（凭 LLM 记忆）时，`unverified`/`uncertain` 占比应**显著高于**有摘要/全书输入。

## 四、覆盖与粒度硬约束（门 `O-COVERAGE` / `O-COUNT`）

- **覆盖**：`topics` 里 distinct `angle` ≥ **3**（不能全挤在一个视角）。
- **粒度**：`topics` 数量 ∈ **[3, 8]**。选题是"值得讲的主题"，不是"全书章节目录复述"。

## 五、banned / placeholder（门 `O-BANNED`）

正文值不得含 `TBD/TODO/待定/待补/占位/适当处理/后续再说/xxx` 等。真实未决项写成 `credibility` 里的 `unverified` + reason，不写成 placeholder。

## 六、最小示例（片段）

```json
{
  "meta": {
    "book": "万历十五年",
    "author": "黄仁宇",
    "input_mode": "title_plus_summary",
    "user_angle_direction": "无",
    "tone": "深度+通俗平衡",
    "knowledge_source": {
      "declaration": "基于用户提供的摘要 + LLM 知识生成；黄仁宇的史观解读为一家之言，成稿前需核实具体史实。",
      "edition": ""
    },
    "selectability": {
      "verdict": "worth_telling",
      "talkable_points_estimate": 5,
      "form": "series",
      "viral_potential": "high",
      "viral_reason": "反常识视角多、能古今对照当下职场"
    }
  },
  "topics": [
    {
      "id": "T01",
      "title": "为什么最勤政的皇帝，反而救不了大明",
      "angle": "counter-intuitive",
      "angle_name": "反常识",
      "hook_directions": [
        "你以为亡国是因为皇帝懒，其实是制度把他锁死了",
        "万历不上朝三十年，不是摆烂，是他唯一能用的反抗"
      ],
      "key_points": [
        "皇帝的勤政和王朝的衰败可以同时发生",
        "文官集团形成的制度惯性，比皇帝个人意志更强",
        "不上朝是消极罢工，不是不管事"
      ],
      "golden_line_direction": "一个人越努力地在一个坏系统里使劲，系统坏得越快",
      "video_form": "single",
      "why_worth_telling": "颠覆'昏君亡国'的常识，钩子最强，适合打头阵",
      "credibility": [
        {"claim": "万历皇帝长期不上朝", "level": "credible", "reason": "全书核心议题，史实公认"},
        {"claim": "文官集团制度惯性导致皇权架空", "level": "uncertain", "reason": "黄仁宇一家之言的史观，非通行共识，讲时需注明"}
      ],
      "title_directions": [
        "最勤政的皇帝，为什么救不了大明",
        "万历三十年不上朝，真相比你想的扎心",
        "他不是昏君，他是被史书写黑了"
      ],
      "cover_direction": "龙椅上一个被锁链困住的皇帝剪影 + 大字'困局'"
    }
  ]
}
```
