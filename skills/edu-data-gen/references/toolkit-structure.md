# 工具包结构约定

> 配合 edu-data-gen skill 的 Checklist 第 4 步。定义产出工具包的目录、文件格式、config 字段、多文件切分、resume 状态。
> `assets/toolkit-template/` 是骨架；为本产品搭工具包时复制它，再填 `config.json`、`prompts/`、`schema/`、`content_list.json`。

---

## 一、工具包目录布局

```
<product>-toolkit/
├── content_list.json      # 要生成的内容点清单
├── config.json            # 产品配置（模型/难度分布/启用门/切分/重试/样本）
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
├── generate.py            # 生成脚本（中断/恢复/重试/幂等/多文件）—— 从模板来
├── validate.py            # 校验门运行器 —— 从模板来
├── README.md              # 使用说明（全量生产用法）
├── state/                 # resume 状态（运行时生成，勿手改）
│   └── state.json
└── output/                # 生成数据（每内容点一个子目录，多文件）
    └── <content_point_id>/
        ├── <slug>.<group1>.json
        └── <slug>.<group2>.json
```

---

## 二、`content_list.json` 格式

内容点清单。每项是一个生成单元。

```jsonc
[
  {
    "id": "material-en-g5-family-parents",   // 唯一；建议 <entity>-<subject>-<grade>-<slug>
    "entity": "material",                      // material|knowledge_point|explanation|item
    "grade": "g5",                             // 难度坐标-年级
    "bloom": "remember",                       // 难度坐标-认知层级（目标）
    "source": "skeleton",                      // skeleton（骨架补全）| generated（从零生成）
    "seed": {"term": "parents"},               // 骨架种子数据；generated 可为 {}
    "knowledge_point_refs": ["kp-en-g5-family"],
    "prompt_template": "material.md"           // prompts/ 下用哪个模板
  }
]
```

- **从零生成模式**：先把"生成大纲/知识点"的内容点（`entity: knowledge_point`, `source: generated`）排在前，素材/讲解/题目引用其 `knowledge_point_refs`。
- 每个内容点的 `entity` 必须在 `schema/` 有对应 schema、在 `prompts/` 有对应模板（`validate_toolkit.py` 查这层对齐）。

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
    "content_list": "content_list.json",
    "schemas_dir": "schema",
    "prompts_dir": "prompts",
    "output_dir": "output",
    "state_file": "state/state.json"
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
    "ref_path": ""                      // builtin: references/curriculum/<subject>.md；user: 用户路径
  },
  "sample": {"size": 20, "seed": 0}     // 样本验证抽样
}
```

---

## 四、多文件切分约定

- 每个内容点的生成结果（一个 JSON 对象）按 `file_split.by_field_group[<entity>]` 切成多个文件，写入 `output/<content_point_id>/`。
- 切分由 generate.py 内的 **字段分组映射** 完成：模板 prompt 让模型按分组返回嵌套对象（如 `{"core": {...}, "examples": [...]}`），generate.py 把每个分组落一个文件 `<slug>.<group>.json`。
- `slug` 取内容点 id 去前缀（如 `parents`）。文件名确定性，便于幂等比对。
- `mode: single_file` 时整对象落一个文件 `<slug>.json`（关掉多文件，仅在产品不需要多文件时用）。

---

## 五、resume 状态（`state/state.json`）

generate.py 每完成一个内容点（写过文件）即追加/更新 state，**支持中断恢复**：

```jsonc
{
  "done": {
    "material-en-g5-family-parents": {
      "model_version": "claude-sonnet-...",   // resp.model 实际值
      "prompt_version": "v1",                  // prompts 模板版本（手填/哈希）
      "files": ["output/material-en-g5-family-parents/parents.core.json",
                "output/material-en-g5-family-parents/parents.examples.json"],
      "generated_at": "2026-06-18T10:00:00"
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

- 如何跑全量：`python generate.py`（自动续跑/重试）。
- 如何强制重跑某项：`python generate.py --only <id>` / `--force`。
- 如何校验：`python validate.py`，看 `validation_report.json`。
- 分布不达标如何定向补：`python generate.py --target-bloom analyze`（补指定坐标题）。
- 多文件输出在哪、resume 状态在哪。
