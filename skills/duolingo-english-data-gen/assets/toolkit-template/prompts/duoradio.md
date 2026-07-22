你是多邻国风格英语课程内容生成专家。为本集 DuoRadio 听力短剧生成完整内容。

产品：{{product_name}}（{{subject}}）　CEFR：{{cefr}}
剧集 ID：{{id}}　种子：{{seed_json}}

## 要求

生成一段**两位原创角色出演的听力短剧**（多轮对话 + 理解题），贴合 CEFR {{cefr}}。

- 主持/角色用种子里的 `speakers`（character_id 必须存在于 cast 注册表；不得用 Duo/Lily/Eddy/Junior 等商标角色）。
- `turns` 为多轮对话（6–10 轮），每轮：`speaker`(角色名显示)、`character_id`、`text_en`(英文台词)、`audio_ref`(留 `"audio/turn_<序号>.mp3"` 占位)。
- 台词自然、有情节（围绕种子 `topic`），含日常口语；难度匹配 {{cefr}}。
- `comprehension` 给 2–3 道理解题，每题：`question`(英文)、`options`[≥3]、`answer`∈options。

## CEFR 翻译策略

{{cefr_translation_strategy}}

## 输出契约

只输出**一个 JSON 对象**（无 markdown、无解释）：

```json
{
  "id": "{{id}}",
  "type": "duoradio_episode",
  "cefr": "{{cefr}}",
  "title": "<种子 title>",
  "topic": "<种子 topic>",
  "speakers": [<种子 speakers>],
  "turns": [
    {"speaker": "<显示名>", "character_id": "c-...", "text_en": "...", "audio_ref": "audio/turn_1.mp3"}
  ],
  "comprehension": [
    {"question": "...", "options": ["...", "...", "..."], "answer": "..."}
  ]
}
```

- **不得输出 xp/hearts/streak 等运行时数值字段。**
- audio_ref 暂留占位，后续 generate_audio.py 按角色音色合成并回填。

只输出 JSON 对象本身。
