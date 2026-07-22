# 质量门定义（多邻国式英语课）

> 配合写/调 validate.py 的门时加载。复用 G1/G2/G5-G8，新增 DL-* 七门。驱动 validate.py。
> 报告格式：`validation_report.json` = `{gates:{<name>:{severity,pass,detail}}, summary:{pass,errors,warnings}}`。放行标准：所有 **ERROR** 门通过。

## 复用门（从 edu-data-gen 移植，适配 CEFR/lesson）

| 门 | 严重 | 查什么 | 通过 |
|---|---|---|---|
| **G1_schema** | ERROR | 每课/每 episode 对其 schema（lesson.json/duoradio_episode.json）做轻量校验（required 非空 + 类型 + enum） | 无违规 |
| **G2_coverage** | ERROR | 每个 content_list id 在 `output/<cefr>/<id>/` 有 ≥1 非 meta 文件；覆盖率 ≥ threshold | 无缺失 |
| **G5_accuracy** | ERROR | choice 类（含 options 的题）answer ∈ options | 全部成立 |
| **G6_age** | WARN | target_sentence/source_text 长度 ≤ CEFR 限（A1=90/A2=110/B1=150/B2=200 字符） | 超长仅 WARN |
| **G7_diversity** | WARN | 同 unit 内 target_sentence 近似重复（Jaccard≥0.85） | 近重仅 WARN |
| **G8_traceability** | ERROR | 每课 `_meta.json` 有 model_version + prompt_version | 齐全 |

## DL-* 门（多邻国专属，新增）

### DL-Type · 题型合法性（ERROR，逐题）
- exercise_type ∈ 13 enum；该类型必填字段非空（见 exercise-types.md 各类型）。
- choice 类 answer ∈ options。
- **禁止** xp/hearts/streak/league/coins/gems 等运行时字段。
- 违规示例：listening 题无 audio_ref；speaking 题无 scoring_rubric；arrange 题无 tokens；出现未知 exercise_type。

### DL-Curve · 难度曲线合规（ERROR，逐课）—— 灵魂
- resolve curve_plan（显式或继承 curve_defaults[cefr]）。
- `len(exercises) == total`；各 stage count 和 = total。
- stages 有序：每题 stage 在 stage_order 中非减。
- 每题 `exercise_type` ∈ 其 stage.allowed_types；`bloom` == 其 stage.bloom。
- **末 stage == end_on_easy；末题 stage == end_on_easy**。

### DL-Distractors · 干扰项质量（ERROR 结构）
- choice 类 distractors ≥3、≠answer、两两不同、answer 不出现在 distractors。
- （合理性 WARN 人审；结构违规 ERROR）

### DL-Translation · 分级翻译策略（ERROR，逐题）—— 编码需求#1
- A1/A2：每题必须有中文（hint_zh/meaning_zh/含中文 accepted_variants）；否则 ERROR。
- B1/B2：不得有完整 meaning_zh（沉浸式）；否则 ERROR。hint_zh 可选。

### DL-Lock · 目标句锁定（ERROR，逐课）—— 编码需求#9
- outline 锁定的 sentence 目标必须出现在某题权威字段（target_sentence/answer/source_text 或 accepted_variants），归一化比较。
- 锁定的 vocab 目标必须在 target_vocab 或某题权威字段。
- 缺失 → ERROR（说明 LLM 漂移，--force 重生或调 prompt）。

### DL-Cast · 角色合法性（ERROR，逐对话/radio）—— 法律风险
- dialogue turns 的 character_id / duoradio speakers 必须 ∈ cast.json 注册表。
- 硬挡商标名（Duo/Lily/Eddy/Junior/Oscar/Bea/Lin/Vikram/Zari/Lucy/Fofo 等）。

### DL-Audio · 音频覆盖（默认 WARN，可配 ERROR）—— generate_audio 后
- 每个 spoken string 有 audio_ref 且 mp3 存在且 size>0。
- **listening/speaking 类型 audio_ref 为空 = ERROR**（schema 层，DL-Type 也查）。
- 其余缺失默认 WARN；`config.dl_audio_strict=true` 时全 ERROR。

## 运行

`python validate.py --root <toolkit>` → 跑全部门，写 validation_report.json，ERROR 门有失败则退码 1。
