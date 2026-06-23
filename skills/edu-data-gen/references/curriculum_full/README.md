# 内置完整课纲库（结构化 JSON）

`curriculum_full/` 是 edu-data-gen 的生产级内置课纲索引，优先作为 `curriculum_alignment.source = builtin` 时的课纲参考。

## 文件

| 学科 | 文件 | 覆盖 |
|---|---|---|
| 数学 | `math.g1-g9.2022.json` | g1-g9，数与代数 / 图形与几何 / 统计与概率 / 综合与实践 |
| 语文 | `zh.g1-g9.2022.json` | g1-g9，识字写字 / 阅读鉴赏 / 表达交流 / 梳理探究 / 整本书阅读 |
| 英语 | `en.g1-g9.2022.json` | g1-g9，主题语境 / 语言知识 / 语言技能；g1-g2 为启蒙扩展 |
| 科学 | `science.g1-g9.2022.json` | g1-g9，科学探究 / 生命科学 / 物质科学 / 地球与宇宙 / 技术工程 |

`schema.json` 描述上述结构化文件的字段约束，供后续自动校验或导入工具使用。

## 数据结构

每个文件包含：

- `standard`：课标来源与官方 URL。
- `coverage`：覆盖年级、领域、知识点总数。
- `grades.<grade>.summary`：该年级知识点数和领域分布。
- `grades.<grade>.knowledge_points[]`：结构化知识点。

知识点字段：

```jsonc
{
  "id": "kp-math-g5-num-02-03",
  "subject": "math",
  "grade": "g5",
  "domain": "数与代数",
  "unit": "因数倍数与分数",
  "title": "分数意义和性质",
  "description": "...",
  "objectives": ["...", "..."],
  "key_exam_points": ["...", "..."],
  "prerequisites": ["kp-math-g4-num-02-01"],
  "difficulty_coordinate": {"grade": "g5", "bloom": "apply"},
  "source": {"type": "official_standard", "name": "...", "url": "..."},
  "order": 8
}
```

## 兼容层

`scripts/build_curriculum_full.py` 会从本脚本内的结构化源生成：

- `references/curriculum_full/*.json`
- `references/curriculum/*.md`

旧版 G9 只解析 Markdown 中的 `kp-*` 行；新版 G9 优先支持 JSON，并保留 Markdown 兼容解析。

## 维护方式

1. 编辑 `scripts/build_curriculum_full.py` 内的 `CURRICULUM`。
2. 运行 `python3 skills/edu-data-gen/scripts/build_curriculum_full.py`。
3. 检查知识点数量、JSON 可解析、兼容 Markdown 中 `kp-*` 数量一致。

不要手改生成出的 JSON/Markdown；否则下次构建会覆盖。
