# 内置课纲与知识点库（语数英科学）

> 配合 edu-data-gen skill 的 P1 课纲对齐能力包。
> 这是 skill 内置的**课纲参考**来源之一（`config.curriculum_alignment.source = builtin` 时被 G9 门引用）。
> **本库为种子库**：覆盖语数英科学常见年级的核心知识点结构，可扩展（见下"如何扩展"）。

---

## 覆盖学科

| 学科 | code | 文件 |
|---|---|---|
| 语文 | `zh` | `chinese.md` |
| 数学 | `math` | `math.md` |
| 英语 | `en` | `english.md` |
| 科学 | `science` | `science.md` |

> 其他学科（政史地、初中物化生细分等）**不在内置库**；需课纲对齐时由用户提供参考（`source: user`），否则 G9 跳过。

---

## id 规约

知识点 id 统一为 `kp-<subject>-<grade>-<slug>`：
- `<subject>`：zh / math / en / science。
- `<grade>`：g3…g9（小三→初三）。
- `<slug>`：知识点英文短_slug（连字符）。

例：`kp-math-g5-fraction-add`（数学·五年级·异分母分数加减）。

内容数据里的 `knowledge_point_refs` 引用这些 id；G9 门校验引用是否落在本库（或用户参考）内、年级是否匹配。

---

## 年级编码

- 小学低：`g3 g4`　小学高：`g5 g6`　初中：`g7 g8 g9`
- （g1/g2 暂未内置，需时扩展）

---

## G9 如何使用本库

1. config 设 `curriculum_alignment.enabled=true`、`source=builtin`、`ref_path=references/curriculum/<subject>.md`。
2. validate.py 解析对应学科文件的 `kp-*` id 集合 + 年级。
3. 对每条生成数据：`knowledge_point_refs` 每个 id 应∈库；若 id 不在库、或其年级≠数据 `grade` → 标"游离于课纲之外"（WARN）。
4. 仅 WARN（不阻断），进报告供人审。

---

## 如何扩展

- 在对应学科文件按既有结构追加 `kp-<subject>-<grade>-<slug>` 行即可。
- 新增学科：新建 `<subject>.md`，沿用 id 规约；非语数英科学 学科默认走 `source=user`（用户自备）。
- 更新后无需改任何脚本（G9 按文件解析 `kp-` 前缀行）。
