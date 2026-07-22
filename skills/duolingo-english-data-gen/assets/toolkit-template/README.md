# 多邻国式英语课 — 数据生成工具包（duolingo-english-data-gen 产出）

把**人审创作的课程骨架**（Section→Unit→Lesson + 原创角色 cast），用 LLM 批量扩写成**多邻国式英语课数据**：每节课 = 12-17 道按难度曲线编排的练习（13 题型），分级翻译策略，目标句锁定，TTS 音频，质量门。
本目录是 duolingo-english-data-gen skill 产出的**可运行工具包**。**全量生产由你执行**；skill 只交付工具包 + 样本验证。

> 灵魂：**单课多题难度曲线**（识别→理解→受限产出→自由产出→结尾简单题），强制结尾留简单题。

## 内容范围（已人审确认）
- CEFR：A1 → B2 全等级（A1/A2 带中文；B1/B2 no-translation 沉浸）
- 13 种练习题型（含口语 speak）
- 内容类型：核心课（lesson）+ DuoRadio 听力短剧
- 原创角色 cast（**非**多邻国商标角色）

## 目录
```
outline/<cefr>.json        人审确认的骨架（Section/Unit/Lesson + locked_targets + curve_plan + duoradio）
cast.json                  原创角色注册表
content_list/<cefr>.json   内容点清单（从 outline 机械展开）
schema/                    exercise/lesson/duoradio_episode/cast schema
prompts/lesson.md          单课生成 prompt（curve slot + 13 题型 + 分级翻译 + 锁定目标）
prompts/duoradio.md        DuoRadio 生成 prompt
config.json                配置（curve_defaults/tts/single_file/DL 门）
generate.py                生成（一节课一次调用、中断/恢复/重试/幂等、单文件原子课）
generate_audio.py          ★ TTS 音频（每 spoken string、角色音色、跨卷 import 逃生口）
validate.py                质量门运行器（G1/G2/G5-G8 + DL-*）
build_android_assets.py    Android 打包（按 CEFR lesson 包 + manifest + cast + 音频）
state/state.json           resume 状态（运行时生成，勿手改）
output/<cefr>/<id>/        生成数据（lesson.json + _meta.json + audio/）
```

## 0. 准备
- `ai_bridge` 需可达：本工具包在 DesignSkills 仓内即可（向上有 `ai_bridge/`）；外移设 `EDU_DATA_GEN_ROOT=<仓库根>`。
- `config.json` 已填好（provider `claude_code`，复用 Claude Code 本地鉴权）。
- `cast.json` 用原创角色（可从 skill 的 `assets/cast.example.json` 复制改名）。

## 四阶段生产流水线

### 1. 生成课数据
```bash
python generate.py              # 所有 CEFR 所有未完成课（自动续跑/重试）
python generate.py --cefr A1    # 只生成某 CEFR
```
- **中断恢复**：Ctrl-C 后重跑，`state.done` 里的自动跳过。
- **失败重试**：失败项进 `state.failed`，下次自动重试（≤ max_retries）。
- 常用：`--cefr A1` / `--limit 5` / `--sample 3` / `--only id1,id2` / `--force` / `--dry-run`。`--only` 默认仍跳过已完成项；需要重生时显式加 `--force`。

### 2. 生成 TTS 音频
```bash
python3 generate_audio.py              # 全量（中断/恢复，已存在 mp3 自动跳过）
python3 generate_audio.py --cefr A1
```
- 为每节课的所有 spoken string（target_sentence/dialogue turns/options 等）合成 mp3，路径内联回 lesson.json。
- ⚠ **跨仓 import**：若本工具包不在含 `tts_providers.py` 的仓库内（如放在 DesignSkills 而 tts_providers 在 LearnEnglish），设：
  ```bash
  export DUOLINGO_TTS_ROOT=/Volumes/JINGZAO/work_space/LearnEnglish
  ```
  （也认 `TTS_PROVIDERS_ROOT` / `EDU_DATA_GEN_ROOT`；找不到会 FAIL FAST 并提示已知路径。）
- 用**系统 `python3`**（含 edge_tts+aiohttp）。
- 常用：`--cefr` / `--only` / `--limit` / `--sample` / `--force` / `--dry-run` / `--provider edge` / `--voice-a/--voice-b`。

### 3. 质量校验
```bash
python validate.py              # 跑全部门，写 validation_report.json
python validate.py --cefr A1    # （如脚本支持）
```
放行标准：所有 **ERROR** 门通过（WARN 仅记录 + 人审抽样）。

### 4. 打包进 Android
```bash
python build_android_assets.py   # 按 CEFR 打 lesson 包 + manifest + cast + 音频拷进 assets
```
> 注：与 app 现有数据消费格式的精确对齐为 follow-up；本脚本按 daily-expression 约定打包。

## 各门含义
- **G1 schema / G2 覆盖 / G8 可追溯**：ERROR，基础结构。
- **G5 准确性**（choice answer∈options）/ **G6 适龄**（长度 WARN）/ **G7 多样性**（近重 WARN）。
- **DL-Type**：13 题型合法 + 作答模式映射 + 各类型必填字段 + 禁运行时数值字段。
- **DL-Content**：必需题型/翻译方向覆盖、图片选项、词块答案、输入归一化、双速听力、结构化对话与非重复收尾。
- **DL-Curve**：难度曲线合规（**末题必为 end_on_easy**、stage 有序、type/bloom 对齐）。
- **DL-Distractors**：干扰项 ≥3/≠answer/不重复。
- **DL-Translation**：A1/A2 必有中文；B1/B2 不得有完整中文释义（沉浸）。
- **DL-Lock**：锁定目标句/词未被偷换。
- **DL-Cast**：角色 ∈ cast 注册表、非商标名。
- **DL-Audio**：listening/speaking 必有 audio_ref（ERROR）；其余音频缺失 WARN（`dl_audio_strict` 可升 ERROR）。

## 人审重点（机判门只兜底）
- 干扰项是否「似是而非」而非太离谱（DL-Distractors 只查结构）。
- B1/B2 沉浸是否彻底（偶尔文化词的 hint_zh 可接受）。
- 锁定目标句是否地道（DL-Lock 只查存在，不查质量）。
- 口语题 scoring_rubric 是否合理。

## 教学内容边界

工具包只生成英语课程内容与教学素材契约：词句、题目、答案、干扰项、释义、解释、图片规格、音频和口语评分标准。不得生成奖励、连击、生命值、打卡、徽章、排行榜、用户状态或页面流程数据。
