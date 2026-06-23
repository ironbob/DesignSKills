# 四类数据实体与 Schema

> 配合 edu-data-gen skill 的 Checklist 第 2-3 步。
> 定义 skill 能生成的四类教育数据实体、字段 schema、示例。**这些是权威模板**；为具体产品推断 schema 时，以此为基础裁剪/扩展，并保证字段能对回页面文档中页面所需的数据。

---

## 通用约定

- 每条数据带 **难度坐标** `difficulty_coordinate: { grade, bloom }`（见 `difficulty-bloom.md`），其中 `grade` 取值如 `g3`…`g9`（小三→初三），`bloom` 取 `remember|understand|apply|analyze|evaluate|create`。
- 每条带 **溯源** `provenance: { model_version, prompt_version, generated_at }`（可追溯门 G8 用）。
- 每条带 `id`（确定性优先：`<type>-<subject>-<grade>-<slug>`，如 `item-en-g5-family-parents`）。
- 凡引用知识点，统一用 `knowledge_point_refs: [<kp_id>...]`，指向知识点与大纲实体。

四类实体：

| 类型 | 实体 | 用途 |
|---|---|---|
| A | 学习素材 / 内容字段 `material` | 单个学习对象（词/概念/公式）的结构化内容 |
| B | 知识点与大纲 `knowledge_point` | 知识点树、考点、年级→主题→课结构 |
| C | 教学讲解 `explanation` | 知识点讲解、例题精讲、方法说明 |
| D | 测验题 `item` | 各题型题目 + 答案 + 解析 + 干扰项 |

---

## A. 学习素材 / 内容字段（`material`）

单个学习对象的完整结构化内容。词汇课的"释义/音标/词性/例句/语境"即此类。

```jsonc
{
  "id": "material-en-g5-family-parents",
  "type": "material",
  "subject": "en",                 // zh|math|en|science|...
  "grade": "g5",
  "term": "parents",               // 学习对象本体（词/概念/公式）
  "pos": "n.",                     // 词性/类型（语言类）
  "phonetic": "/ˈpeərənts/",       // 音标/读法（语言类；数学可空）
  "definitions": ["父母"],          // 释义（可多义项）
  "context_sentence": "My parents are very kind.",  // 语境例句
  "examples": [                    // 补充例句
    {"en": "I live with my parents.", "zh": "我和父母住在一起。"}
  ],
  "audio_desc": "需要 TTS：英式/美式各一",   // 素材描述字段（不产音频本身）
  "image_desc": "可选：一家三口温馨插画",     // 素材描述字段（不产图本身）
  "knowledge_point_refs": ["kp-en-g5-family"],
  "difficulty_coordinate": {"grade": "g5", "bloom": "remember"},
  "provenance": {"model_version": "...", "prompt_version": "v1"}
}
```

字段裁剪：非语言类去掉 `pos/phonetic`；数学概念把 `term` 换成概念名、加 `formula`。

---

## B. 知识点与大纲（`knowledge_point`）

知识点树节点 + 大纲结构。"从零生成"模式下，先批量产出此类构成大纲，再挂素材/讲解/题目。

```jsonc
{
  "id": "kp-math-g5-fraction-add",
  "type": "knowledge_point",
  "subject": "math",
  "grade": "g5",
  "title": "异分母分数加减法",
  "parent_id": "kp-math-g5-fraction",   // 树结构
  "order": 3,                            // 同级排序
  "summary": "通分后按同分母分数加减法计算",
  "objectives": ["能找到最小公分母", "能正确通分并加减"],
  "prerequisites": ["kp-math-g4-fraction-concept", "kp-math-g5-common-multiple"],
  "key_exam_points": ["通分步骤", "结果约分"],
  "difficulty_coordinate": {"grade": "g5", "bloom": "apply"}
}
```

大纲层级：`grade → theme(主题) → unit(课) → knowledge_point`。`theme`/`unit` 可作为 `knowledge_point` 的祖先节点（`type` 同为 `knowledge_point`，层级靠 `parent_id` 表达）。

> **大纲节点 ≠ 生成的 knowledge_point 实体**：建工具包前，skill 先产**大纲**（`outline/<grade>.json`，人审确认）——大纲节点在本实体字段基础上**多一个 `generation_plan`**（`{explanation, material, items_by_bloom}`），声明"该 KP 生成几个素材/讲解/各层级几题"。`generation_plan` 只用于**机械展开成 `content_list/`**，**不进**生成的 knowledge_point 数据本身。大纲节点格式与展开规则见 `outline-generation.md`。

---

## C. 教学讲解（`explanation`）

知识点讲解 / 例题精讲 / 方法说明，"教"的内容。

```jsonc
{
  "id": "exp-math-g5-fraction-add",
  "type": "explanation",
  "subject": "math",
  "grade": "g5",
  "knowledge_point_ref": "kp-math-g5-fraction-add",
  "title": "怎样做异分母分数加减法",
  "bloom": "understand",
  "segments": [                          // 讲解正文（分段，便于多文件/多区渲染）
    {"heading": "为什么要通分", "body": "..."},
    {"heading": "通分三步", "body": "1. 找最小公分母 ..."}
  ],
  "worked_example": {"problem": "1/2 + 1/3", "steps": ["通分→3/6+2/6", "相加→5/6"], "answer": "5/6"},
  "common_mistakes": ["忘记约分", "分母直接相加"],
  "difficulty_coordinate": {"grade": "g5", "bloom": "understand"},
  "provenance": {"model_version": "...", "prompt_version": "v1"}
}
```

---

## D. 测验题（`item`）

各题型题目 + 标准答案 + 解析 + 干扰项。"测"的核心，也是难度分层的主要载体。

```jsonc
{
  "id": "item-math-g5-fraction-add-q1",
  "type": "item",
  "subject": "math",
  "grade": "g5",
  "question_type": "choice",            // choice|fill|judge|short|essay|spell|...
  "stem": "1/2 + 1/3 = ?",
  "options": ["5/6", "2/5", "1/5", "1/6"],   // choice 必填
  "answer": "5/6",                      // 标准答案
  "distractors": ["2/5", "1/5", "1/6"], // 干扰项（≠ answer，需 plausible）
  "explanation": "异分母先通分：1/2=3/6, 1/3=2/6，相加得 5/6。",
  "solution_steps": ["通分→3/6+2/6", "相加→5/6"],
  "knowledge_point_refs": ["kp-math-g5-fraction-add"],
  "difficulty_coordinate": {"grade": "g5", "bloom": "apply"},
  "provenance": {"model_version": "...", "prompt_version": "v1"}
}
```

题型字段差异：
- `choice`：必填 `options`(≥4)、`answer`∈`options`、`distractors`≥3 且均≠`answer`。
- `fill`：`answer` 为字符串（可多空用列表）；无 `options`。
- `judge`：`options`=["对","错"]、`answer`∈其中。
- `short`/`essay`：`answer` 为参考答案；可带 `answer_rubric`。
- `spell`：`answer` 为目标拼写；接受常见变体可列 `accepted_variants`。

---

## 推断产品 schema 的方法

1. 读页面文档（epps.json）：每个页面 `sample_state` 与 `density.zones[]` 暴露它**消费**哪些字段（如 `example_word.{w,ph,gloss,pos,ex}`）→ 这些字段必须出现在对应实体 schema。
2. 读需求文档：功能清单里的"学习项/题目/讲解"决定要哪几类实体、每类哪些字段。
3. 以本文四类模板为基底，裁剪无关字段、补充产品特有字段；保证**页面消费的字段 ↔ schema 字段 ↔ 生成脚本输出映射**三者对齐（`validate_toolkit.py` 会查这层对齐）。
