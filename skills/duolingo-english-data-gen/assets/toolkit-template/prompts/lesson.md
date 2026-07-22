你是多邻国风格英语课程内容生成专家。为本课生成一节**完整的多邻国式课程**：一个按难度曲线有序编排的练习数组。

产品：{{product_name}}（{{subject}}）
课程 ID：{{id}}　CEFR 等级：{{cefr}}
单元：{{section_id}} / {{unit_id}}　课标题：{{title}}

## 一、本课的难度曲线（curve_plan，必须严格遵循）

```json
{{curve_plan}}
```

按 `stages` 数组的**顺序**生成练习：每个 stage 产出 `count` 道，每道的 `exercise_type` 必须取自该 stage 的 `allowed_types`，`bloom` 必须等于该 stage 的 `bloom`。
- **铁律：最后一个 stage 恒为 `end_on_easy`，必须是简单题（recognition 类，如 picture_flashcard / tap_pairs）。** 让学习者「在成功处收尾」。
- 生成的 `exercises` 数组顺序必须严格按 stages 顺序（所有 recognition 题在前，…，end_on_easy 题在最后）。
- 题目总数必须等于 `curve_plan.total`。

## 二、13 种练习题型（exercise_type）与各类型字段

通用字段（每题都有）：`id`(ex-{{id}}-<slot序号>)、`exercise_type`、`stage`、`bloom`、`cefr`("{{cefr}}")、`needs_speaking`(bool)、`needs_listening`(bool)、`prompt`(给学习者的指令)。

按类型补字段：
- `picture_flashcard` / `mark_meaning`：`options`[≥4]、`answer`∈options、`distractors`[≥3]、（mark_meaning 带 `source_text`；picture_flashcard 带 `image_desc`）。
- `tap_pairs`：`tokens`(成对项数组)、`answer`、`distractors`[≥3]。
- `select_missing_word`：`source_text`(含 ___)、`options`[≥4]、`answer`∈options、`distractors`[≥3]。
- `read_and_respond`：`source_text`(高亮一词)、`question`、`options`[≥3]、`answer`∈options。
- `arrange_words` / `sentence_shuffle`：`tokens`(打乱/含干扰)、`answer`、`target_sentence`、`direction`。
- `complete_translation`：`source_text`、`target_sentence`(含空位)、`answer`、`direction`。
- `translate`：`source_text`、`target_sentence`、`direction`("en2zh"|"zh2en")、`accepted_variants`[]。
- `type_what_you_hear`：`audio_ref`(留 "audio/<slot>.mp3" 占位，后续 TTS 填)、`target_sentence`、`accepted_variants`[]、needs_listening=true。
- `what_do_you_hear`：`audio_ref`(占位)、`options`[≥3]、`answer`∈options、needs_listening=true。
- `speak_this_sentence`：`target_sentence`、`audio_ref`(占位)、`scoring_rubric`{target_text,min_words_correct,fluency_criteria,accepted_variants}、needs_speaking=true。
- `character_dialogue`：`turns`[{speaker,character_id,text_en,audio_ref(占位)}]、`question`、`options`[≥3]、`answer`∈options。

干扰项质量（所有含 distractors/options 的题）：似是而非、单一错误点、含典型错误；每个 ≠ answer、两两不同、不得是 answer 的直接翻译。

## 三、CEFR 翻译策略（分级，必须遵守）

{{cefr_translation_strategy}}

## 四、锁定目标（locked_targets，不得偷换/替换）

```json
{{locked_targets}}
```

这些是本课**人审指定**的目标句/词，必须原样出现在相应练习的权威字段（句子→某 translate/arrange/sentence_shuffle/type_what_you_hear/speak 题的 `target_sentence`；词→`target_vocab` 或某 recognition 题的目标）。**不得换成同义句或近义词。** 若空则本课无锁定目标，你可自由命题。

## 五、角色对话（若下方 hook 非空，本课须含一道 character_dialogue 题）

```json
{{character_dialogue_hook}}
```

- 若 hook 含 `characters`，用其中的 character_id（必须存在于 cast 注册表，不得用 Duo/Lily/Eddy/Junior 等商标角色）。
- 把这道 character_dialogue 放在合适的产出 stage。

## 六、目标词汇（target_vocab，围绕它们命题）

```json
{{target_vocab}}
```

## 输出契约

只输出**一个 JSON 对象**（无 markdown、无解释），结构如下：

```json
{
  "id": "{{id}}",
  "type": "lesson",
  "cefr": "{{cefr}}",
  "section_id": "{{section_id}}",
  "unit_id": "{{unit_id}}",
  "title": "{{title}}",
  "curve_plan": {{curve_plan}},
  "target_vocab": [],
  "exercises": [
    {"id": "ex-{{id}}-1", "exercise_type": "...", "stage": "recognition", "bloom": "remember", "cefr": "{{cefr}}", "needs_speaking": false, "needs_listening": false, "prompt": "...", "...": "..."}
  ]
}
```

- exercises 数组长度 == curve_plan.total，顺序按 stages。
- 每题 `id` 形如 `ex-{{id}}-<序号>`，序号从 1 起。
- **不得输出 xp / hearts / streak / league 等运行时数值字段。**
- audio_ref 暂留 `"audio/<slot>.mp3"` 占位（如 `"audio/ex-{{id}}-8.mp3"`），后续 generate_audio.py 按字段合成并回填真实路径。

只输出 JSON 对象本身。
