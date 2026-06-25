# 工具包结构约定

> 配合 edu-data-gen skill 的 Checklist 第 4 步。定义产出工具包的目录、文件格式、config 字段、多文件切分、resume 状态。
> `assets/toolkit-template/` 是骨架；为本产品搭工具包时复制它，再填 `config.json`、`prompts/`、`schema/`、`outline/`、`content_list/`。

---

## 一、工具包目录布局

```
<product>-toolkit/
├── outline/               # 【人审确认的大纲】按年级分文件 —— 先确认，再展开
│   ├── g1.json  g2.json … g9.json
├── content_list/          # 【内容点清单】按年级分文件（从 outline 机械展开）
│   ├── g1.json  g2.json … g9.json
├── config.json            # 产品配置（模型/难度分布/启用门/切分/重试/样本/大纲默认）
├── schema/                # 实体 schema（material/knowledge_point/explanation/item）
│   ├── material.json
│   ├── knowledge_point.json
│   ├── explanation.json
│   └── item.json
├── prompts/               # prompt 模板（每实体一个，{{占位}}）
│   ├── material.md
│   ├── knowledge_point.md
│   ├── explanation.md
│   └── item.md
├── generate.py            # 生成脚本（中断/恢复/重试/幂等/多文件/按年级）—— 从模板来
├── validate.py            # 校验门运行器 —— 从模板来
├── README.md              # 使用说明（全量生产用法）
├── state/                 # resume 状态（运行时生成，勿手改；按内容点 id，天然分年级）
│   └── state.json
└── output/                # 生成数据（按年级 → 每内容点一个子目录，多文件）
    └── <grade>/
        └── <content_point_id>/
            ├── <slug>.<group1>.json
            └── <slug>.<group2>.json
```

> **大纲 vs 内容列表**：`outline/` 是人审确认的粗粒度计划（知识点 + 每个 KP 生成多少）；`content_list/` 是从大纲**机械展开**的细粒度 leaf 清单。生成规则见 `outline-generation.md`。

---

## 二、`outline/` 与 `content_list/` 格式

### 2.1 `outline/<grade>.json` —— 人审确认的大纲（按年级）

权威定义见 `outline-generation.md` §四。每文件一个年级：

```jsonc
{
  "subject": "en",
  "grade": "g5",
  "source": "generated",                  // skeleton | builtin | generated
  "summary": {"kp_count": 6, "est_units": 72},
  "knowledge_points": [
    {
      "id": "kp-en-g5-family",
      "title": "Family members",
      "parent_id": "kp-en-g5-unit1",
      "order": 1,
      "prerequisites": [],
      "difficulty_coordinate": {"grade": "g5", "bloom": "understand"},
      "generation_plan": {                // 该 KP 生成多少（三条杠杆产物）
        "explanation": 1,
        "material": 8,
        "material_seeds": [                // 可选；表达/词汇等有限素材集合必须提供
          {"term": "parents"},
          {"term": "grandparents"}
        ],
        "items_by_bloom": {"remember": 3, "understand": 3, "apply": 2}
      }
    }
  ]
}
```

- **用户确认的就是这一层**（范围 + 数量 + 难度）。确认/改完才展开。

### 2.2 `content_list/<grade>.json` —— 展开后的内容点清单（按年级）

`outline` 经确定性规则（`outline-generation.md` §五）展开而来。每项是一个生成单元：

```jsonc
[
  {
    "id": "material-en-g5-family-m1",       // 唯一；<entity>-<subject>-<grade>-<slug>-<seq>
    "entity": "material",                     // material|knowledge_point|explanation|item
    "grade": "g5",                            // 难度坐标-年级
    "bloom": "remember",                      // 难度坐标-认知层级（目标）
    "source": "generated",                    // 承自 outline 文件的 source
    "seed": {"knowledge_point": "Family members", "term": "parents"},
    "knowledge_point_refs": ["kp-en-g5-family"],
    "prompt_template": "material.md"          // prompts/ 下用哪个模板
  }
]
```

- 每个内容点的 `entity` 必须在 `schema/` 有对应 schema、在 `prompts/` 有对应模板（`validate_toolkit.py` 查这层对齐）。
- `content_list/` 的条目数必须等于 `outline/` 各 KP `generation_plan` 的展开预期，且计划难度分布达标——`validate_toolkit.py` 强校验（§八）。
- 若大纲 `generation_plan.material_seeds` 存在，`content_list` 中该 KP 展开的每条 `material` 必须逐条继承对应 seed。表达类产品应使用 `{"sentence": "...", "meaning": "...", "function": "..."}` 作为 seed，避免多个素材只靠序号自由生成而互相重复。

---

## 三、`config.json` 字段

```jsonc
{
  "product": {"name": "英语词汇课", "subject": "en", "default_grade": "g5"},
  "llm": {
    "provider": "claude_code",          // 固定（claude_code_direct provider 的注册名）
    "generate_model": "sonnet",         // 生成模型别名：sonnet|opus|haiku
    "judge_model": "sonnet",            // 可选：主观项 LLM-as-judge（默认不用）
    "temperature": 0.7,
    "max_tokens": 2048,
    "max_retries": 3,                   // 单内容点 LLM 调用/解析失败重试上限
    "timeout": 120
  },
  "paths": {
    "outline_dir": "outline",          // 人审大纲目录（按年级分文件）
    "content_list": "content_list",    // 内容点清单目录（按年级分文件；展开自 outline）
    "schemas_dir": "schema",
    "prompts_dir": "prompts",
    "output_dir": "output",
    "state_file": "state/state.json"
  },
  "outline_defaults": {                // 从零生成大纲时，KP 无显式 plan 的默认（见 outline-generation.md §三）
    "generation_plan": {"explanation": 1, "material": 8, "items_total": 8}
  },
  "file_split": {
    "mode": "by_field_group",           // by_field_group | single_file
    "by_field_group": {                 // 每实体把输出对象切成多个文件（键=分组名）
      "material": ["core", "examples"],
      "item": ["stem_options", "answer_explain"],
      "explanation": ["body", "worked_example"],
      "knowledge_point": ["outline"]
    }
  },
  "difficulty_distribution": {                   // 按年级段，见 difficulty-bloom.md
    "g1-g2": {"remember": 0.55, "understand": 0.32, "apply": 0.13},
    "g3-g4": {"remember": 0.45, "understand": 0.35, "apply": 0.18, "analyze": 0.02},
    "g5-g6": {"remember": 0.35, "understand": 0.32, "apply": 0.25, "analyze": 0.08},
    "g7-g9": {"remember": 0.22, "understand": 0.28, "apply": 0.25, "analyze": 0.18, "evaluate": 0.07}
  },
  "distribution_tolerance_pp": 15,       // G4 分布容差（百分点）
  "coverage_threshold": 1.0,             // G2 覆盖阈值
  "gates": {                             // 启用哪些门；P0 默认全 true
    "G1_schema": true, "G2_coverage": true, "G3_question": true,
    "G4_distribution": true, "G5_accuracy": true,
    "G6_age": true, "G7_diversity": true, "G8_traceability": true,
    "G9_curriculum": false
  },
  "curriculum_alignment": {              // G9 用
    "enabled": false,
    "source": "none",                   // builtin | user | none
    "ref_path": ""                      // builtin: references/curriculum_full/<subject>.g1-g9.2022.json；user: 用户路径
  },
  "sample": {"size": 20, "seed": 0}     // 样本验证抽样
}
```

---

## 四、多文件切分约定

- 每个内容点的生成结果（一个 JSON 对象）按 `file_split.by_field_group[<entity>]` 切成多个文件，写入 `output/<grade>/<content_point_id>/`（按年级归档）。
- 切分由 generate.py 内的 **字段分组映射** 完成：模板 prompt 让模型按分组返回嵌套对象（如 `{"core": {...}, "examples": [...]}`），generate.py 把每个分组落一个文件 `<slug>.<group>.json`。
- `slug` 取内容点 id 去前缀（如 `parents`）。文件名确定性，便于幂等比对。
- `mode: single_file` 时整对象落一个文件 `<slug>.json`（关掉多文件，仅在产品不需要多文件时用）。

---

## 五、resume 状态（`state/state.json`）

generate.py 每完成一个内容点（写过文件）即追加/更新 state，**支持中断恢复**：

```jsonc
{
  "done": {
    "material-en-g5-family-m1": {
      "content_point_id": "material-en-g5-family-m1",
      "entity": "material",
      "grade": "g5",                            // ← 决定 output 落在 output/<grade>/<id>/
      "bloom": "remember",
      "model_version": "claude-sonnet-...",     // resp.model 实际值
      "prompt_version": "sha1:1a2b3c4d",        // prompts 模板内容哈希
      "files": ["output/g5/material-en-g5-family-m1/m1.core.json",
                "output/g5/material-en-g5-family-m1/m1.examples.json"]
    }
  },
  "failed": {
    "item-math-g5-fraction-add-q7": {"attempts": 3, "last_error": "JSON parse failed"}
  }
}
```

- **幂等**：重跑时跳过 `done` 里的 id（除非 `--force`）；只处理未完成 + `failed`。
- **重试**：`failed` 里的 id 在 `max_retries` 内重试；超限则保留在 `failed` 并标"待修复/人审"。
- 中断（Ctrl-C / 异常）后重跑：已落盘的 done 项不丢、不重生成。

---

## 六、prompt 模板（`prompts/*.md`）

每实体一个 markdown 模板，含 `{{占位}}`（grade/bloom/seed/schema_json/...）。generate.py 渲染占位后发给 LLM，要求**按字段分组返回 JSON**（与 `file_split` 对齐）。模板里写清：输出 JSON 结构、难度坐标要求、约束（如选择题干扰项规则）、禁止幻觉。

---

## 七、使用说明（`README.md`）必须含

- **大纲先确认**：`outline/<grade>.json` 是人审确认的计划；改大纲后需重新展开 `content_list/`（由 skill 在建工具包时做，用户一般不手改 content_list）。
- 如何跑全量：`python generate.py`（遍历所有年级，自动续跑/重试）。
- 如何只跑某年级：`python generate.py --grade g5`（分年级生成/续跑/重试）。
- 如何强制重跑某项：`python generate.py --only <id>` / `--force`。
- 如何校验：`python validate.py`，看 `validation_report.json`。
- 分布不达标如何定向补：`python generate.py --target-bloom analyze`（补指定坐标题）。
- 多文件输出在哪（`output/<grade>/<id>/`）、resume 状态在哪。

---

## 八、`validate_toolkit.py` 对大纲的校验

工具包自校验新增两类检查（无大纲时跳过，仅 WARN）：

1. **展开自洽（ERROR）**：每个有 `outline/<grade>.json` 的年级，`content_list/<grade>.json` 各 entity 条目数 == 大纲各 KP `generation_plan` 展开预期：
   - `knowledge_point` = KP 数；`material` = Σ plan.material；`explanation` = Σ plan.explanation；`item` = Σ Σ items_by_bloom。
   - 不一致 → ERROR（skill 必须在 3b 修正展开）。
2. **素材 seed 一致性（ERROR）**：若 KP 写了 `material_seeds`，其长度必须等于 `generation_plan.material`，同一 KP 内 target（优先 `sentence`，其次 `term/concept/title/name`）不得重复，且展开后的 `content_list` material seed 必须包含对应 target。
3. **计划难度分布（WARN）**：该年级 `item` 的计划 Bloom 占分 vs `config.difficulty_distribution[年级段]`，偏差超 `distribution_tolerance_pp` → WARN（运行时 G4 门为硬约束，这里仅预检）。

> 这两类把"人审大纲 → 机械展开"的契约变成可机判的门：展开错了当场拦下，不等到全量生产才发现。
