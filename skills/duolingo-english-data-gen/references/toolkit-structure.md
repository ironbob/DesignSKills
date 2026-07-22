# 工具包结构约定（多邻国式英语课）

> 配合搭工具包（Checklist 4）、写 README 时加载。镜像 edu-data-gen 的 `toolkit-structure.md`，差异：CEFR 取代年级、单文件原子课、curve_defaults、tts 块、cast.json。

## 目录

```
<课程>-toolkit/
├── outline/<cefr>.json     人审确认的骨架（a1/a2/b1/b2：Section/Unit/Lesson + locked_targets + curve_plan + duoradio_episodes）
├── cast.json               原创角色注册表（id/name/persona/voice）
├── content_list/<cefr>.json 内容点清单（从 outline 机械展开：每 lesson/每 radio 1 点）
├── schema/                 exercise/lesson/duoradio_episode/cast schema
├── prompts/                lesson.md / duoradio.md
├── generate.py             生成（一节课一次调用、中断/恢复/重试/幂等、单文件原子课、--cefr）
├── generate_audio.py       TTS 音频（每 spoken string、角色音色、跨卷 import 逃生口）
├── validate.py             校验门（G1/G2/G5-G8 + DL-*）
├── build_android_assets.py Android 打包（按 CEFR lesson 包 + manifest + cast + 音频）
├── config.json             配置（curve_defaults/tts/single_file/DL 门）
├── state/state.json        resume 状态（运行时生成）
├── output/<cefr>/<id>/     生成数据（lesson.json + _meta.json + audio/）
└── README.md               使用说明（四阶段全量用法）
```

## config.json 字段

| 字段 | 用途 | 谁读 |
|---|---|---|
| `product.{name,subject,default_cefr}` | 产品名/subject=en/默认 CEFR | generate |
| `llm.{provider,generate_model,temperature,max_tokens,max_tokens_by_level,max_retries}` | LLM 调用；max_tokens_by_level 按 CEFR 给（A1=4096/B2=8192） | generate |
| `paths.{outline_dir,content_list,schemas_dir,prompts_dir,output_dir,state_file,cast_file}` | 各目录/文件 | 全部 |
| `curve_defaults.{A1,A2,B1,B2}` | 各 CEFR 默认 curve_plan（outline 课节点可省略继承） | generate/validate/validate_toolkit |
| `file_split.mode` | 恒 `single_file`（一节课=一文件） | generate |
| `coverage_threshold` | G2 覆盖阈值（1.0） | validate |
| `dl_audio_strict` | DL-Audio 是否 ERROR（默认 false=WARN） | validate |
| `gates.{G1,G2,G5,G6,G7,G8,DL_Type,DL_Curve,DL_Distractors,DL_Translation,DL_Lock,DL_Cast,DL_Audio}` | 各门开关 | validate |
| `tts.{provider,default_voice,voice_a,voice_b,rate,concurrency,max_retries}` | TTS 配置（走 tts_providers.py 工厂） | generate_audio |
| `sample.{size,seed}` | 样本验证默认 | run_sample_validation |

## 单文件原子课（file_split.mode=single_file）

- 一节课 = `output/<cefr>/<lesson_id>/lesson.json`（含全部 exercises + curve_plan + target_vocab）。
- 同目录 `_meta.json`（provenance：model_version + prompt_version）。
- DuoRadio episode → `output/<cefr>/<radio_id>/duoradio.json`。
- cast → `cast.json`（tk 根，人审输入）；build_android 拷进 assets。
- 覆盖 edu-data-gen 的 by_field_group 默认；validate 的 load_entities 直接读单文件。

## resume 状态（state/state.json）

```json
{"done": {"<id>": <meta>}, "failed": {"<id>": {"attempts": N, "last_error": "..."}}}
```
- generate 每节课后 persist（中断安全）；重跑跳过 done（除非 --force）；failed 自动重试。
- id 稳定 → 改大纲只动变化条目，resume 状态不丢。

## 四阶段生产流水线（README 须写清）

1. `generate.py`（生成课数据）→ 2. `generate_audio.py`（TTS）→ 3. `validate.py`（过门）→ 4. `build_android_assets.py`（打包）。
