# Exercise Types — 多邻国 13 种练习题型规格

> 配合 SKILL.md 写 `prompts/lesson.md` 与 `validate.py` 的 DL-Type 门时加载。
> 这是 13 题型的**唯一权威菜单**。lesson prompt 内嵌其精简版；DL-Type 门按每类型的必填字段判定。

## 通用字段（13 种都有）

`id` · `exercise_type` · `interaction_mode` · `stage` · `bloom` · `cefr` · `needs_speaking` · `needs_listening` · `prompt`(只写操作指令) · `hint_zh`/`meaning_zh`/`explanation_zh`(教学反馈)。题目原文必须放 `source_text`，不得藏在 prompt 中。

> 游戏化红线：exercises **不得**含 `xp`/`hearts`/`streak`/`league` 等运行时数值字段。DL-Type 门拒绝未知顶层字段。

## 13 题型（按 stage 归类）

### Recognition 认知（bloom=remember）—— 最易，只识别不产出
| exercise_type | 测什么 | 必填字段（DL-Type 查） | 音频/评分 |
|---|---|---|---|
| `picture_flashcard` | 按词选图/看图选词 | `options[]` ≥4，每项 `{id,text,image_ref,image_prompt,audio_ref}`，A1/A2 另需 `label_zh`；`answer`=option.id；`distractors[]` ≥3 | 每个 option 有发音；图片为教学素材契约 |
| `tap_pairs` | 左右两列点对配对 | `tokens[]`(成对项), `answer`(正确配对集), `distractors[]` | tokens 可选发音 |
| `mark_meaning` | 选哪个句子/词是正确翻译 | `options[]` ≥4, `answer`∈options, `source_text`, `distractors[]` ≥3 | — |

### Understanding 理解（bloom=understand）
| exercise_type | 测什么 | 必填字段 | 音频/评分 |
|---|---|---|---|
| `select_missing_word` | 句子留空选词填入 | `source_text`(含___), `options[]` ≥4, `answer`∈options, `distractors[]` ≥3 | — |
| `read_and_respond` | 高亮一词选其含义 | `source_text`, `question`, `options[]` ≥3, `answer`∈options | — |
| (`mark_meaning` 也常落此段) | | | |

### Constrained production 受限产出（bloom=apply）—— 词都给，受限拼
| exercise_type | 测什么 | 必填字段 | 音频/评分 |
|---|---|---|---|
| `arrange_words` | 打乱词排成正确句 | `tokens[]`, `answer_tokens[]`(权威顺序), `target_sentence` | target_sentence 可发音 |
| `sentence_shuffle` | 词库拼翻译（含干扰词） | `source_text`, `tokens[]`, `answer_tokens[]`, `target_sentence`, `direction` | 英文一侧可发音；支持 en2zh/zh2en |
| `complete_translation` | 翻译缺一词补全 | `source_text`, `target_sentence`(含空位), `answer`, `direction` | target_sentence 发音 |

### Free production 自由产出（bloom=apply）—— 无脚手架
| exercise_type | 测什么 | 必填字段 | 音频/评分 |
|---|---|---|---|
| `translate` | 整句打字翻译/改写 | `source_text`, `target_sentence`, `direction`(en2zh/zh2en/en2en), `accepted_variants[]`, `normalization` | target_sentence 可发音 |
| `type_what_you_hear` | 听音频逐字转录 | `audio_ref`, `slow_audio_ref`, `target_sentence`, `accepted_variants[]`, `normalization` | 正常/慢速音频都必须 |
| `what_do_you_hear` | 听音选正确文本 | `audio_ref`, `slow_audio_ref`, `target_sentence`, `options[]` ≥3, `answer`∈options | 正常/慢速音频都必须 |
| `speak_this_sentence` | 朗读入麦 | `target_sentence`, `audio_ref`(示范音), **`scoring_rubric`** 必填 | scoring_rubric 见下 |

### 角色（可落 free_production 或独立）
| exercise_type | 测什么 | 必填字段 | 音频/评分 |
|---|---|---|---|
| `character_dialogue` | 角色多轮对话 + 语境选答 | `turns[]`(每项 `speaker_id`+`character_id`+`text_en`+`audio_ref`), `question`, `options[]` ≥3, `answer`∈options | 每 turn 按角色发音；DL-Cast 查 character_id |

## 作答模式固定映射

`single_choice`：picture_flashcard / mark_meaning / select_missing_word / read_and_respond；`pair_match`：tap_pairs；`word_bank`：arrange_words / sentence_shuffle；`text_input`：complete_translation / translate；`listening_input`：type_what_you_hear；`listening_choice`：what_do_you_hear；`speaking`：speak_this_sentence；`dialogue_choice`：character_dialogue。

自由输入与听写题的 `normalization` 至少声明：`strip_whitespace`、`case_sensitive`、`normalize_punctuation`、`ignore_terminal_punctuation`。标准答案与可接受变体是教学内容；用户本次作答、得分、连击等不是。

## speak_this_sentence 的 scoring_rubric（运行时 ASR 评分契约，ASR 本身不在本 skill 范围）

```jsonc
"scoring_rubric": {
  "target_text": "Good morning!",
  "min_words_correct": 2,           // 至少正确词数
  "key_phonemes": ["ɡʊd", "mɔːnɪŋ"], // 关键音标（可选）
  "fluency_criteria": "no long pause; natural rhythm",
  "accepted_variants": ["good morning", "mornin'"]
}
```

## 干扰项质量（DL-Distractors 查；适用于一切有 distractors/options 的题）

- 数量按题型：4 选项题（picture_flashcard / mark_meaning / select_missing_word）≥3 干扰项；3 选项题（read_and_respond / what_do_you_hear）≥2 干扰项。
- 门把 `distractors` 字段与 `options` 里的非答案项都算作有效干扰项（取较多者），兼容 LLM 把错误选项放 options 而非单列 distractors。
- 每个干扰项 ≠ `answer`；两两不同。
- 不得是 answer 的直接翻译（懒干扰）。
- 似是而非、单一错误点、含典型错误（dead giveaways）—— 结构违规 ERROR，合理性 WARN（人审）。

## CEFR 适配建议（写 prompt 时参考，非硬约束）

- **A1/A2**：偏 recognition + constrained；干扰项用常见混淆词；每题带中文释义/翻译（见 difficulty-curve.md 翻译策略）。
- **B1/B2**：加大 free_production（translate / type_what_you_hear / speak）；干扰项更微妙；no-translation，英文释义学新词。
- 口语题 `speak_this_sentence` 在 A1 可少（约 1 道/课），B2 可增到 2–3 道。
