# 大纲生成规则（outline-generation）

> 配合 edu-data-gen skill 的 Checklist 第 3a 步。
> 定义**大纲（outline）**怎么生成、装什么、怎么展开成内容列表。**产出/确认大纲时加载**。
> 核心原则：**人只确认大纲（语义）；内容列表由大纲机械展开，过门校验，不再人审。**

---

## 一、为什么大纲要独立成"先确认"的阶段

大纲（教什么、各生成多少）是地基。大纲错了，后面工具包（schema/prompt/脚本）全白做。
所以 skill 把"产出大纲 → 用户确认"提到**建工具包之前**（Checklist 3a），这是**最便宜、最早**的人工门。
确认后才展开成内容列表（3b，机械），再搭工具包（4）。

---

## 二、大纲 ≠ 内容列表（务必分清）

| | 大纲 outline | 内容列表 content_list |
|---|---|---|
| 粒度 | 粗：知识点 + 每个 KP 生成多少 | 细：每道题/每个素材（leaf 单元） |
| 行数 | 几十~一两百 | 上千 |
| 谁确认 | **人审 + 确认（可改）** | **机器从大纲展开 + 过 validate_toolkit** |
| 性质 | 语义（教什么/多少/多难） | 机械（展开 q1/q2/q3…） |

> 内容列表上千行不该让人逐行确认——那是 `validate_toolkit.py` + `validate.py` 门的事。
> 大纲是**人能读完、能拍板**的那一层。

---

## 三、三条杠杆：范围 / 数量 / 难度

大纲每个 KP 由三条规则决定：

### 杠杆 1 · 范围（KPs 从哪来）——按优先级取

| 模式 | KP 来源 | outline `source` |
|---|---|---|
| 有种子骨架 | 骨架里的 KP | `skeleton` |
| 语数英科学 + 课纲对齐开 | 内置完整库 `references/curriculum_full/<subject>.g1-g9.2022.json`（按 g1…g9 分段），每段 → 该年级 KP；旧式工具包可退回 `references/curriculum/<subject>.md` | `builtin` |
| 都没有（从零） | skill 从【需求功能清单 + 页面内容区】推断，**保守提案**：1 主题 → 2-4 课 → 每 KP 聚焦一个学习目标 | `generated` |

> **从零的边界（YAGNI）**：提案一个克制的树，不贪多。用户在确认环节增删。每条 KP 标 `source`，便于 G9 课纲对齐门分辨来源。

### 杠杆 2 · 数量（generation_plan）——默认 + config 覆盖 + 可改

每个 KP 给一套 `generation_plan`。来源优先级：

1. 该 KP 显式写的 `generation_plan`（最高）。
2. `config.outline_defaults.generation_plan`（产品级默认）。
3. skill 内置默认：`{explanation: 1, material: 8, items_total: 8}`。

`generation_plan` 字段：

```jsonc
"generation_plan": {
  "explanation": 1,                 // 该 KP 生成几个讲解（默认 1）
  "material": 8,                    // 该 KP 生成几个素材（默认 8；词汇类≈词条数）
  "material_seeds": [               // 可选但强烈建议；表达/词汇等有限集合必须提供
    {"term": "parents"},
    {"term": "grandparents"}
  ],
  "items_by_bloom": {               // 该 KP 各认知层级出几题（见杠杆 3）
    "remember": 3, "understand": 3, "apply": 2
  }
}
```

> 用户在确认环节可逐项改（"这个核心 KP 多出 5 题""讲解只要 1 个"）。

#### 素材目标数组：避免同一 KP 下重复生成

当 `material` 代表一个**有限学习对象集合**时，大纲阶段必须一次性给出 `material_seeds`，不要只给空槽位数量：

- 英语日常表达/句型：每个 seed 至少包含 `sentence`，可补 `meaning`、`function`、`scenario`、`register`、`pattern`。
- 英语词汇：每个 seed 至少包含 `term`，可补 `meaning`、`pos`、`scenario`。
- 数学/科学概念：每个 seed 至少包含 `concept` 或 `term`，可补 `representation`、`misconception`。

示例（表达类）：

```jsonc
"generation_plan": {
  "explanation": 0,
  "material": 4,
  "material_seeds": [
    {"sentence": "May I borrow your pencil?", "meaning": "我可以借用你的铅笔吗？", "function": "礼貌借物"},
    {"sentence": "Can you go over it one more time?", "meaning": "你能再讲一遍吗？", "function": "请求重复讲解"},
    {"sentence": "Who wants to share their answer?", "meaning": "谁想分享一下自己的答案？", "function": "课堂互动"},
    {"sentence": "I'm stuck on this question.", "meaning": "这道题把我卡住了。", "function": "表达卡住"}
  ],
  "items_by_bloom": {}
}
```

规则：

1. 若写了 `material_seeds`，其长度必须等于 `generation_plan.material`。
2. 同一 KP 的 `material_seeds` 不得重复；表达类按 `sentence` 去重，词汇/概念按 `term|concept` 去重。
3. 后续 `content_list` 展开只继承 seed，不再让 LLM 自由决定"这条素材学哪一句/哪个词"。
4. 对 `material >= 5` 的语言类 KP，除非是开放素材池，否则应提供 `material_seeds`；否则容易出现多个槽位都生成同一个句型骨架（如反复围绕 borrow）。

### 杠杆 3 · 难度（items_by_bloom）——由 `config.difficulty_distribution` 驱动

`items_by_bloom` 不靠拍脑袋，按规则算：

1. 该 KP 所属年级落在哪个**年级段**（g5 → `g5-g6` 段）。
2. 取 `config.difficulty_distribution[段]` 的占比比例。
3. × 该 KP 的 `items_total`（= Σ items_by_bloom 目标）**四舍五入取整**，凑成 `items_total`。

示例：g5（段 `g5-g6` = {remember .35, understand .32, apply .25, analyze .08}），`items_total = 8`
→ remember 2.8≈3 / understand 2.56≈3 / apply 2.0≈2 / analyze 0.64≈0 → `{remember:3, understand:3, apply:2}`，合计 8。✓

> 不足/超出 `items_total` 的余数，按占比最大的档补齐（这里 analyze 被舍掉，正常——小样本取整）。

---

## 四、大纲节点 schema（权威定义）

大纲按**年级分文件**：`outline/<grade>.json`（如 `outline/g5.json`）。每个文件：

```jsonc
{
  "subject": "en",
  "grade": "g5",
  "source": "generated",                 // skeleton | builtin | generated（该年级统一来源）
  "summary": {                           // 人审用，可选但建议
    "kp_count": 6,
    "est_units": 72                      // 展开后该年级内容点总数（见 §五）
  },
  "knowledge_points": [
    {
      "id": "kp-en-g5-family",           // kp-<subject>-<grade>-<slug>
      "title": "Family members",
      "parent_id": "kp-en-g5-unit1",     // 父节点（theme/unit）id；顶级 null
      "order": 1,
      "prerequisites": [],               // [kp id...] 前置知识点
      "difficulty_coordinate": {"grade": "g5", "bloom": "understand"},  // 该 KP 基准难度
      "generation_plan": {               // ← §三 三条杠杆的产物
        "explanation": 1,
        "material": 8,
        "material_seeds": [{"term": "parents"}, {"term": "grandparents"}],
        "items_by_bloom": {"remember": 3, "understand": 3, "apply": 2}
      }
    }
  ]
}
```

> `theme`/`unit` 也是大纲节点（`parent_id` 串成树），但通常不挂 `generation_plan`（它们是分组，不直接出题/素材）；只有叶子 KP 带 `generation_plan`。

---

## 五、展开规则（大纲 → 内容列表，确定性，不再人审）

用户确认大纲后，skill **机械展开**成 `content_list/<grade>.json`。每个 KP 节点 `k`（年级 `g`、学科 `s`、slug = `k.id` 去 `kp-<s>-<g>-` 前缀）展开为：

| 展开条目 | 数量 | id | entity | bloom | knowledge_point_refs |
|---|---|---|---|---|---|
| 知识点本体 | 1 | `k.id` | `knowledge_point` | `k.difficulty_coordinate.bloom` | `[]` |
| 素材 | `k.generation_plan.material` | `material-<s>-<g>-<slug>-m<i>` | `material` | `remember` | `[k.id]` |
| 讲解 | `k.generation_plan.explanation` | `explanation-<s>-<g>-<slug>-e<i>` | `explanation` | `understand` | `[k.id]` |
| 题目 | Σ `items_by_bloom` | `item-<s>-<g>-<slug>-q<seq>` | `item` | 该桶 bloom | `[k.id]` |

- 题目 `seq` 为 KP 内递增序号，按固定 Bloom 顺序（remember→understand→apply→analyze→evaluate→create）分配，保证**确定性、id 稳定**。
- 素材 `seed` 带 `{knowledge_point: k.title}` + `material_seeds[i-1]`（若大纲提供；如 `sentence`/`term`/`concept`）；题目 `seed` 带 `{knowledge_point: k.title, bloom_hint}`。
- `est_units`（§四 summary）= Σ_KP (1 + material + explanation + Σ items_by_bloom)。

**确定性是关键**：大纲只改了某 KP → 只有该 KP 的内容点 id 变化，其余 KP 的 id 不变 → resume 状态（按 id）天然保留，重跑只补新内容点。

> 展开后**不再人审**：`validate_toolkit.py` 校验"内容列表条目数 == 大纲各 KP plan 展开预期"+"计划难度分布达标"（见 quality-gates / toolkit-structure）。

---

## 六、确认流程（Checklist 3a）

1. skill 按三条杠杆产出 `outline/<grade>.json`（每个涉及年级一份）。
2. 汇总呈给用户：每年级 KP 数、est_units、计划难度分布。
3. 用户**确认或要求修改**（增删 KP、调 `generation_plan` 数量/难度）。
4. 改完**重新确认**，直到 OK。
5. 确认通过 → 进 3b 机械展开。

> 反模式：跳过大纲确认直接展开+建工具包；或让人逐行确认上千条内容列表。两者都违反"人审大纲、机判内容列表"。

---

## 七、与各参考的关系

- 范围来源：`references/curriculum_full/`（内置完整库）、`references/curriculum/`（兼容索引）、用户骨架。
- 难度比例：`config.difficulty_distribution`（定义见 `difficulty-bloom.md` §三）。
- 展开后的内容点格式：`toolkit-structure.md` §二。
- 展开自洽校验：`scripts/validate_toolkit.py`。
- KP 实体定义：`data-types-and-schemas.md` §B（大纲节点在其基础上加 `generation_plan`，但 `generation_plan` 不进生成数据本身）。
