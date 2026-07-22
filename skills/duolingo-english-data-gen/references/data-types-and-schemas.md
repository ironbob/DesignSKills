# 数据实体与 schema（多邻国式英语课）

> 配合 SKILL.md 推断数据需求、写 schema/outline/content_list 时加载。
> 生成单元 = **一节课（lesson）**，含 12-17 道有序 exercise。区别于 edu-data-gen 的「单内容点」。

## 一、实体总览

| 实体 | 是什么 | outline(人审) | content_list(机械) | 生成输出 |
|---|---|---|---|---|
| `course` | 顶层元数据（A1→B2 路径、cast 引用） | 1 节点 | — | 1 文件 |
| `section` | 一个 CEFR 波段下的 units 分组（如 Rookie） | 是 | — | 1 文件 |
| `unit` | section 内一个单元，有主题 + 有序 lessons | 是 | — | 1 文件 |
| `lesson` | **生成单元**：12-17 道按曲线编排的练习 | 是（叶子，带 curve_plan + locked_targets） | 1 内容点 | **1 原子文件** |
| `exercise` | 13 题型之一 | 否（生成） | 否（内联于 lesson） | 内联在 lesson 文件 |
| `duoradio_episode` | DuoRadio 听力短剧（多轮音频 + 理解题） | 是（独立流） | 1 内容点 | 1 文件 |
| `cast` | 原创角色注册表 | 是（outline 顶部 cast_ref） | 引用不展开 | 1 文件 `cast.json` |

> `course/section/unit` 在 outline 是结构节点；可选择性生成（MVP 可只生成 lesson + duoradio + cast，section/unit 作为路径元数据内联进 lesson 文件的 `section_id`/`unit_id`）。

## 二、outline（人审骨架）— `outline/<cefr>.json`（a1/a2/b1/b2 各一）

```jsonc
{
  "course": "duolingo-english-original",
  "cefr": "A1",
  "cast_ref": "cast.json",
  "sections": [
    {"id": "sec-a1-rookie", "title": "Rookie", "order": 1, "units": [
      {"id": "unit-a1-1-greetings", "title": "Greetings", "order": 1, "theme": "saying hello",
       "lessons": [
         {"id": "lesson-a1-1-1-hi", "title": "Say Hi", "order": 1,
          "cefr": "A1",
          "target_vocab": ["hello","hi","good morning"],
          "locked_targets": [
            {"kind":"sentence","text":"Good morning!"},
            {"kind":"vocab","text":"hello"}
          ],
          "curve_plan": {/* 见 difficulty-curve.md；可省略继承 config.curve_defaults.A1 */},
          "character_dialogue_hook": {"characters":["c-mia","c-tom"],"topic":"morning greeting"}
         }
       ]}
    ]}
  ],
  "duoradio_episodes": [
    {"id":"radio-a1-1","title":"Coffee & Greetings","cefr":"A1","speakers":["c-mia","c-nora"],"topic":"ordering coffee"}
  ]
}
```

- 这是**人审创作的种子**（像 seeds.py）。skill 只展开每节 lesson + 每 radio episode。
- `locked_targets` 锁定目标句/词，防 LLM 偷换（DL-Lock）。
- `character_dialogue_hook` 告诉生成器这课要含一道 `character_dialogue` 题（角色见 cast_ref）。

## 三、content_list（机械展开）— `content_list/<cefr>.json`，顶层数组

每节 lesson → 1 内容点；每 radio → 1 内容点：

```jsonc
[
  {"id":"lesson-a1-1-1-hi","entity":"lesson","cefr":"A1",
   "section_id":"sec-a1-rookie","unit_id":"unit-a1-1-greetings",
   "curve_plan":{/* resolved：继承或显式 */},
   "seed":{"locked_targets":[...],"target_vocab":[...],"character_dialogue_hook":{...},"title":"Say Hi"},
   "prompt_template":"lesson.md"},
  {"id":"radio-a1-1","entity":"duoradio_episode","cefr":"A1",
   "seed":{"speakers":["c-mia","c-nora"],"title":"Coffee & Greetings","topic":"ordering coffee"},
   "prompt_template":"duoradio.md"}
]
```

- `entity` ∈ {lesson, duoradio_episode}；选 schema 文件 + 默认 prompt。
- 每内容点 = 一次 LLM 调用 = 一个输出文件。id 稳定 → 改大纲只动变化条目、resume 状态不丢。

## 四、生成输出（单文件原子）— `output/<cefr>/<id>/lesson.json`

```jsonc
{
  "id":"lesson-a1-1-1-hi","type":"lesson","cefr":"A1",
  "section_id":"sec-a1-rookie","unit_id":"unit-a1-1-greetings","title":"Say Hi",
  "curve_plan":{...},
  "exercises":[ <15 个 exercise 对象，按 stage 有序> ],
  "target_vocab":[...]
}
```

- **`file_split.mode = single_file`**：一节课 = 一个文件含全部 exercise（需求：单文件原子，App 整课消费）。覆盖 edu-data-gen 的 by_field_group 默认。
- `_meta.json` 同目录（provenance：model_version + prompt_version，G8）。
- DuoRadio episode → `output/<cefr>/<radio_id>/duoradio.json`。
- cast → `output/cast.json`（或 toolkit 根，由 build_android 决定）。

## 五、exercise 联合 schema（见 `schema/exercise.json` + `exercise-types.md`）

- 单一 schema：`exercise_type` enum(13) + 通用 required 字段；按类型分支的必填字段由 **DL-Type 门**判定（不是 13 个 schema）。
- 通用字段：id, exercise_type, stage, bloom, cefr, needs_speaking, needs_listening, prompt, audio_ref, hint_zh。
- 按类型：choice→options/answer/distractors；word-bank→tokens/target_sentence；translation→source_text/direction/accepted_variants；listening→audio_ref+target_sentence；speaking→target_sentence/scoring_rubric；dialogue→turns[]/question/options/answer。
- **红线**：exercise 不得含 xp/hearts/streak/league（运行时数值归 app）。
