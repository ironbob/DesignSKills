# Difficulty Curve — 难度曲线引擎 + CEFR 翻译策略

> 配合 SKILL.md 写 `prompts/lesson.md`、`config.json` 的 `curve_defaults`、`validate.py` 的 DL-Curve/DL-Translation 门时加载。
> **这是本课的灵魂**（多邻国「一节课 = 按曲线编排的有序练习序列，结尾留简单题」）。

## 一、曲线不是 prompt 嘱咐，是数据结构

prompt-only（「请按识别→…→简单收尾出 15 题」）不可验证、会漂移。「强制结尾简单题」「比例可配」都是机器可判的契约，因此必须是**数据**，由新增 DL-Curve 门机械校验。

每节课的 `curve_plan` 是一个**有序 slot 列表**，LLM 按 slot 填空，门校验生成结果与 plan 镜像一致。

## 二、curve_plan 结构（挂在 outline 课节点；可省略继承 config.curve_defaults[CEFR]）

```jsonc
"curve_plan": {
  "total": 15,
  "stages": [
    {"stage": "recognition",            "count": 5, "bloom": "remember",   "allowed_types": ["picture_flashcard","tap_pairs","mark_meaning"]},
    {"stage": "understanding",          "count": 4, "bloom": "understand", "allowed_types": ["select_missing_word","read_and_respond","mark_meaning","character_dialogue"]},
    {"stage": "constrained_production", "count": 3, "bloom": "apply",      "allowed_types": ["arrange_words","sentence_shuffle","complete_translation"]},
    {"stage": "free_production",        "count": 2, "bloom": "apply",      "allowed_types": ["translate","type_what_you_hear","speak_this_sentence"]},
    {"stage": "end_on_easy",            "count": 1, "bloom": "remember",   "allowed_types": ["picture_flashcard","tap_pairs"]}
  ]
}
```

### 硬约束（validate_toolkit 预检 + DL-Curve 运行时查）
1. `stages` 是**有序数组**——生成的 exercise 顺序必须按此 stage 顺序。
2. **末 stage 恒为 `end_on_easy`，bloom=remember**（多邻国铁律：在成功处收尾）。
3. 各 stage `count` 之和 == `total`。
4. 每个 stage 的 `allowed_types` ⊂ 13 题型 enum（见 exercise-types.md）。
5. 生成的每道题：`exercise_type` ∈ 其所在 stage 的 `allowed_types`；`bloom` == 其 stage 的 `bloom`；`stage` 字段 == 其 stage 名。
6. 每课可声明 `required_exercise_types` 与 `required_translation_directions`；前者必须能在 curve_plan 的 allowed_types 中落位，后者必须是 en2zh/zh2en/en2en。A1/A2 可要求双向中英翻译，B1/B2 可要求 en2en 改写。DL-Content 机械检查实际覆盖。

### 五个 stage 的认知含义
- **recognition** 认：只识别（看图选词/配对/选释义）—— 最低启动门槛。
- **understanding** 懂：在语境中理解（选词填空/阅读理解）。
- **constrained_production** 受限产出：词都给，拼成句（排列/词库/补全翻译）。
- **free_production** 自由产出：无脚手架（整句翻译/听写/朗读）。
- **end_on_easy** 收尾：回到最易题，制造「我做到了」的正反馈。

## 三、CEFR 默认曲线模板（config.curve_defaults，骨架可省略继承）

| CEFR | recognition | understanding | constrained | free | end_on_easy | total | 说明 |
|---|---|---|---|---|---|---|---|
| A1 | 6 | 4 | 3 | 1 | 1 | 15 | 重识别，少自由产出/口语 |
| A2 | 5 | 4 | 3 | 2 | 1 | 15 | 略增产出 |
| B1 | 3 | 4 | 4 | 3 | 1 | 15 | 产出占比上升 |
| B2 | 2 | 3 | 4 | 5 | 1 | 15 | 重自由产出 + 口语 |

> outline 课节点的 `curve_plan` 可省略 → 展开时继承 `config.curve_defaults[该课CEFR]`；也可显式覆盖（如某课专门练口语）。`validate_toolkit` 校验「省略则继承、显式则合法」。

## 四、CEFR 翻译策略（DL-Translation 门，编码需求「低阶带中文/高阶沉浸」）

| CEFR | 中文策略 | 门判定 |
|---|---|---|
| **A1 / A2** | **必须带中文**：每题 `hint_zh`/`meaning_zh`/翻译题的中文非空；翻译题可双向 | 任一 exercise 无中文 → ERROR |
| **B1 / B2** | **no-translation 沉浸**：用英文释义学新词；`meaning_zh` 必须空/缺；`hint_zh` 仅可选作「提示」（短，不是完整释义） | 出现完整中文释义 → ERROR；hint_zh 可有可无 |

> 合理例外：B 级遇到文化不可译词（如节日名）允许短 `hint_zh`，但不得把整句/整义翻成中文。门只挡「full gloss」，不挡「hint」——阈值在 prompt 里约束 + 人审。

## 五、防漂移（DL-Lock 门）

每课 outline 带 `locked_targets`（锁定的目标句/词）。生成后，`_post_process` 把锁定的目标串**重注入**权威字段（translate/arrange 的 `answer`/`target_sentence`；type_what_you_hear 的 `target_sentence`）。DL-Lock 门归一化（去空格/大小写/标点）比较 + 允许 `accepted_variants` 兜底。保证骨架定的目标句不被 LLM 偷换。

## 六、生成流（generate.py 一次调用产一节课）

1. content_list 每课内容点带 resolved `curve_plan` + `locked_targets` seed → 渲染进 lesson.md prompt。
2. prompt 把 curve_plan 呈现为有序 slot 列表（「slot1–6=recognition，允许 X/Y/Z；…slot15=end_on_easy」）+ 13 题型菜单 + required_exercise_types/required_translation_directions + CEFR 翻译策略 + 锁定目标。
3. LLM 返回 `{"meta":…, "exercises":[<有序 15 题>]}`（一次调用，保曲线连贯）。
4. `_post_process` 重注入锁定目标 + 防御性按 stage 稳定排序（不造 stage）。
5. DL-Curve/DL-Type/DL-Content/DL-Translation/DL-Lock 门逐课校验。
