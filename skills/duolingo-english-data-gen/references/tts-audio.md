# TTS 音频约定（多邻国式英语课）

> 配合写/用 generate_audio.py、搭工具包（Checklist 4）、排查音频问题时加载。
> TTS 能力复用共享 `tts_providers.py`（`create_provider()` 工厂），不在本工具包内重实现。

## 一、哪些字段合成音频

generate_audio.py 扫描每节课/每集的所有 spoken string：

- **exercise 级 audio_ref**（listening/speaking 类）：`type_what_you_hear` / `what_do_you_hear` / `speak_this_sentence` 的 `audio_ref` + `target_sentence` → 合成 `target_sentence` 的发音。
- **听力 slow_audio_ref**：同一 target_sentence 用 `config.tts.slow_rate` 再合成一份慢速音频，不能复用普通音频文件。
- **picture_flashcard options[].audio_ref**：按 option.text 合成目标词发音。
- **character_dialogue 的 turns[].text_en** → 每轮一句，按角色音色。
- **duoradio 的 turns[].text_en** → 每轮一句，按角色音色。
- 其余 recognition/understanding/constrained 类（看图选词/选词填空等）不强求音频（DL-Audio 不查）；如 LLM 设了 audio_ref 占位且有 target_sentence，也会合成。

合成后把真实路径内联回对应字段（exercise 的 `audio_ref`、turn 的 `audio_ref`），原子写回 JSON，build_android_assets 自动带进 app。

## 二、角色音色映射（原创 cast）

- `cast.json` 每角色 `{id, name, persona, voice}`。
- 对话 turn 按 `character_id` 查 cast 的 `voice`；cast 没声明的角色按首次出现顺序交替 `voice_a`/`voice_b`。
- 非角色旁白（exercise 的 target_sentence）用 `config.tts.default_voice`。
- **不用**多邻国商标角色（Duo/Lily/Eddy/Junior…）；DL-Cast 门会挡。

## 三、⚠ 跨仓 import（头号运行时坑）

`tts_providers.py` 可能与本工具包**不在同一仓库**（如工具包在 DesignSkills，tts_providers 在 LearnEnglish）。向上走找不到时，设环境变量（按优先级）：

```bash
export DUOLINGO_TTS_ROOT=/Volumes/JINGZAO/work_space/LearnEnglish   # 首选
# 或 TTS_PROVIDERS_ROOT / EDU_DATA_GEN_ROOT 指向含 tts_providers.py 的目录
```

找不到会 **FAIL FAST** 并提示已知路径（`/Volumes/JINGZAO/work_space/LearnEnglish/tts_providers.py`），不静默跳过音频。

## 四、运行

```bash
python3 generate_audio.py                 # 全量（中断/恢复，已存在 mp3 跳过）
python3 generate_audio.py --cefr A1
python3 generate_audio.py --only lesson-a1-1-1-hi
python3 generate_audio.py --sample 3 --seed 0
python3 generate_audio.py --force         # 强制重生
python3 generate_audio.py --dry-run
python3 generate_audio.py --provider edge --voice-a en-US-AriaNeural --voice-b en-US-GuyNeural --slow-rate=-30%
```

- 用**系统 `python3`**（含 edge_tts+aiohttp）。
- 幂等：mp3 存在且非空则跳过；并发默认 8；单 clip 失败退避重试。
- 换 provider：改 `config.tts.provider`（edge/iflytek/tencent/glm）+ 对应环境变量 key；voice 名按 provider 不同。

## 五、与校验的关系

- DL-Audio 门（validate.py）：listening/speaking 类型 audio_ref 为空 = ERROR；听力题 slow_audio_ref 为空同样 ERROR；其余音频缺失默认 WARN（`config.dl_audio_strict=true` 升 ERROR）。
- 顺序：`generate.py` → `generate_audio.py` → `validate.py`（音频补齐后再校验 DL-Audio）。
