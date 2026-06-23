# 质量校验门定义

> 配合 edu-data-gen skill。定义工具包内置 validate.py 的各道质量门：**查什么 / 严重级别 / 可机判判定 / 通过标准**。
> 原则：**能机判的全机判**（schema/覆盖/干扰项/分布/去重/可追溯/音标格式等）；主观准确性走人审抽样，不靠模型自评当门。

严重级别：
- **ERROR** = 阻断（不通过不放行 / 标记待修复）。
- **WARN** = 警告（标记，进报告，不强制阻断）。

---

## P0 门（核心，必启）

### G1 · schema 一致（ERROR，逐条）
- **查**：每条输出是否符合对应实体 schema（必填字段齐全、类型正确、枚举值合法）。
- **判**：JSON Schema 校验（`material/knowledge_point/explanation/item` 各自 schema）。
- **过**：所有条目 schema 合法。失败条目标记 `schema_error`，进 fix loop。

### G2 · 覆盖 / 完整性（ERROR，批级）
- **查**：`content_list/` 各年级每个内容点都有对应输出；无空文件、无空必填。
- **判**：输出内容点 id 集合 ⊇ 内容列表 id 集合；每个内容点产出文件数 ≥ 切分规则下限。
- **过**：覆盖率达阈值（默认 **100%**）。

### G3 · 题目有效性（ERROR，逐条，仅 `item.choice`）
- **查**：`options` ≥ 4；`answer` ∈ `options`；`distractors` ≥ 3 且每项 ∉ {answer}；`options` 无重复；`stem` 非空。
- **判**：纯集合/字符串判定。
- **过**：所有选择题满足。常见违规：干扰项含正确答案、多个正确答案、选项重复。

### G4 · 难度分布（ERROR/WARN，批级，仅 `item`）
- **查**：各 Bloom 实际占比 vs `config.difficulty_distribution` 目标（按年级段）。
- **判**：见 `difficulty-bloom.md` §五。目标档实际为 0 → ERROR；占比偏差 > 容差(默认 15pp) → WARN。
- **过**：无 ERROR 级分布违规。

### G5 · 准确性（可机判部分）（ERROR，逐条）
- **查机器能判的事实错误**：
  - 音标 `phonetic` 形如 `/.../`（含斜杠、非空）；非法格式 → 违规。
  - 选择题 `answer` 在 `options` 内（与 G3 重叠，独立报）。
  - `explanation`/`solution_steps` 的最终结果与 `answer` 一致（解析末值 == answer，字符串归一比较）。
  - 语言类 `pos` 与 `definitions` 形态自洽（如 `pos=n.` 但释义是完整句子 → 可疑，WARN）。
- **判**：正则 + 归一比较。
- **过**：无可机判事实错误。**主观准确性**（释义是否地道、解析是否真对）不在此门，走人审抽样。

> 说明：G5 只覆盖"机器一眼能判"的硬错误。把"LLM 自评准确性"当门是反模式（自评不可靠）。

---

## P1 门（标准版启用）

### G6 · 适龄（WARN，逐条）
- **查**：内容难度/用语与 `grade` 匹配。
- **判（启发式）**：词数/句长阈值（如小三题目 stem 词数不过长、不出现超纲术语）；词汇难度粗判。
- **过**：仅 WARN，标记疑似超龄/低龄，进报告供人审。

### G7 · 多样性 / 去重（WARN，批级）
- **查**：题干/素材/例句无高度雷同。
- **判**：对 `stem`/`term`/`context_sentence` 做近似重复检测（归一后 Jaccard/编辑距离阈值，默认相似度 ≥ 0.85 视为重复）。
- **过**：重复项标记去重/待审。

### G8 · 可复现 / 可追溯（ERROR，批级）
- **查**：每条带 `provenance.model_version` 与 `prompt_version`。
- **判**：字段非空。
- **过**：全量可追溯（任一条缺失即 ERROR——否则无法回溯/重生成）。

---

## P1 能力包：课纲对齐

### G9 · 课纲对齐（WARN，逐条，可选）
- **启用条件**：config `curriculum_alignment.enabled = true` 且有课纲参考（用户提供或内置库）。
- **查**：`knowledge_point_refs` 指向的知识点在所选课纲参考内；内容游离于课纲之外（知识点不在课纲、或年级不符）。
- **判**：优先读取结构化 JSON 课纲（`curriculum_full/*.json` 的 id/年级/领域/标题），旧式 Markdown 则退回解析 `kp-*` id 集合。
- **过**：仅 WARN，标记游离项。非 语数英科学 学科无内置库时，需用户提供参考，否则该门跳过。

---

## 报告格式

validate.py 产 `validation_report.json`：

```jsonc
{
  "summary": {"total": 120, "errors": 3, "warnings": 7, "pass": false},
  "gates": {
    "G1_schema":       {"severity": "ERROR", "pass": false, "failures": [<id>...]},
    "G2_coverage":     {"severity": "ERROR", "pass": true,  "coverage": 1.0},
    "G3_question":     {"severity": "ERROR", "pass": true,  "failures": []},
    "G4_distribution": {"severity": "ERROR", "pass": true,
                        "actual": {"remember": 0.34, "understand": 0.30, "apply": 0.28, "analyze": 0.08},
                        "target": {...}, "max_dev_pp": 12},
    "G5_accuracy":     {"severity": "ERROR", "pass": true,  "failures": []},
    "G6_age":          {"severity": "WARN",  "pass": true,  "flagged": [<id>...]},
    "G7_diversity":    {"severity": "WARN",  "pass": true,  "duplicates": [[<id>,<id>]...]},
    "G8_traceability": {"severity": "ERROR", "pass": true},
    "G9_curriculum":   {"severity": "WARN",  "pass": true,  "off_curriculum": [], "enabled": true}
  }
}
```

**放行标准**：所有 **ERROR 门 pass=true**（WARN 不阻断，但进报告 + 人审抽样）。样本验证与全量生产共用此标准。
