# 内置课纲与知识点库（语数英科学）

> 配合 edu-data-gen skill 的 P1 课纲对齐能力包。
> `references/curriculum_full/*.json` 是结构化完整库；本目录 `*.md` 是由完整库生成的兼容索引，供旧版 G9 和人工快速浏览使用。
> `config.curriculum_alignment.source = builtin` 时，优先指向 `references/curriculum_full/<subject>.g1-g9.2022.json`。

---

## 覆盖学科

| 学科 | code | 文件 |
|---|---|---|
| 语文 | `zh` | `curriculum_full/zh.g1-g9.2022.json` / `curriculum/chinese.md` |
| 数学 | `math` | `curriculum_full/math.g1-g9.2022.json` / `curriculum/math.md` |
| 英语 | `en` | `curriculum_full/en.g1-g9.2022.json` / `curriculum/english.md` |
| 科学 | `science` | `curriculum_full/science.g1-g9.2022.json` / `curriculum/science.md` |

> 其他学科（政史地、初中物化生细分等）**不在内置库**；需课纲对齐时由用户提供参考（`source: user`），否则 G9 跳过。

---

## id 规约

知识点 id 统一为 `kp-<subject>-<grade>-<slug>`：
- `<subject>`：zh / math / en / science。
- `<grade>`：g1…g9（小一→初三）。
- `<slug>`：知识点英文短_slug（连字符）。

例：`kp-math-g5-num-02-05`（数学·五年级·异分母分数加减法）。

内容数据里的 `knowledge_point_refs` 引用这些 id；G9 门校验引用是否落在本库（或用户参考）内、年级是否匹配。

---

## 年级编码

- 小学低：`g1 g2 g3 g4`　小学高：`g5 g6`　初中：`g7 g8 g9`
- 英语 `g1/g2` 为启蒙扩展层，便于低龄产品使用；若产品只按国家课程从三年级起步，可在生成大纲时跳过。

---

## G9 如何使用本库

1. config 设 `curriculum_alignment.enabled=true`、`source=builtin`、`ref_path=references/curriculum_full/<subject>.g1-g9.2022.json`。
2. validate.py 解析对应学科 JSON 的 `knowledge_points[]`（id/年级/领域/标题）；旧版 Markdown 仍可解析 `kp-*` id 集合 + 年级。
3. 对每条生成数据：`knowledge_point_refs` 每个 id 应∈库；若 id 不在库、或其年级≠数据 `grade` → 标"游离于课纲之外"（WARN）。
4. 仅 WARN（不阻断），进报告供人审。

---

## 如何扩展

- 编辑 `scripts/build_curriculum_full.py` 的 `CURRICULUM`，再运行该脚本生成 JSON + Markdown 兼容索引。
- 新增学科：新增结构化 JSON 并沿用知识点字段；非语数英科学 学科默认走 `source=user`（用户自备）。
- Markdown 文件是生成物，不建议手改。
