# 数据生成工具包（edu-data-gen 产出）

本目录是 edu-data-gen skill 为某教育产品产出的**数据生成工具包**。
用途：用 `generate.py` 批量生成该产品的教学/测验数据，`validate.py` 跑质量门。**全量生产由你执行**。

## 目录

```
outline/<grade>.json   人审确认的大纲（知识点 + 每 KP 生成多少；按年级分文件）
content_list/<grade>.json  内容点清单（从 outline 机械展开；按年级分文件）
config.json            产品配置（模型/难度分布/启用门/切分/重试/样本/大纲默认）
schema/                实体 schema（material/item/explanation/knowledge_point）
prompts/               prompt 模板（每实体一个，{{占位}}）
generate.py            生成脚本（中断/恢复/重试/幂等/每点多文件/按年级）
validate.py            质量门运行器（G1-G9）
state/state.json       resume 状态（运行时生成，勿手改；按内容点 id，天然分年级）
output/<grade>/<id>/   生成数据（每点多文件 + _meta.json 溯源）
```

> **大纲先确认**：`outline/` 是 skill 产出、你确认过的计划（教哪些、各生成多少、多难）。
> `content_list/` 是从大纲**机械展开**的清单——一般不手改；要改范围就改 `outline/` 再让 skill 重新展开。

## 1. 准备
- 确认 `config.json` 已填（复制自 `config.example.json`）。
- 确认 `outline/`、`content_list/`、`schema/`、`prompts/` 就绪（skill 已按产品填好）。
- `ai_bridge` 需可达：本工具包在 DesignSkills 仓库内即可；外移时设 `EDU_DATA_GEN_ROOT=<仓库根>`。

## 2. 全量生成
```bash
python generate.py                 # 生成所有年级所有未完成内容点（自动续跑/重试）
python generate.py --grade g5      # 只生成某一年级（分年级跑/续跑/重试）
```
- **中断恢复**：Ctrl-C 后重跑，已完成的（`state.done`）自动跳过。
- **失败重试**：失败项进 `state.failed`，下次重跑自动重试（≤ `config.llm.max_retries`）；超限标"待人审"。

## 3. 常用选项
```bash
python generate.py --grade g5          # 只跑某年级
python generate.py --limit 50          # 只跑下 50 个（分批）
python generate.py --sample 30         # 随机抽 30 个
python generate.py --only id1,id2      # 只重跑指定项
python generate.py --target-bloom analyze   # 只跑某认知层级（补分布用）
python generate.py --force             # 强制重跑（忽略已 done）
python generate.py --dry-run           # 只列计划，不调 LLM
```

## 4. 质量校验
```bash
python validate.py                    # 跑 G1-G9，写 validation_report.json
```
- 放行标准：所有 **ERROR 门** 通过（WARN 仅记录+人审）。
- 难度分布不达标（G4）→ 用 `generate.py --target-bloom <档>` 定向补题，再校验。

## 5. 多文件输出
每个内容点在 `output/<grade>/<id>/` 下按 `config.file_split.by_field_group` 切成多个文件
（如 material → `*.core.json` + `*.examples.json`），并附 `_meta.json`（模型版本/prompt 版本，可追溯）。
`validate.py` 会把它们合并回扁平实体再过 schema 门。

## 6. 课纲对齐（可选）
`config.curriculum_alignment.enabled=true` 时，`validate.py` 的 G9 门校验内容知识点是否落在课纲参考内。
`source=builtin` 用 skill 内置 语数英科学完整 JSON 库（推荐 `references/curriculum_full/<subject>.g1-g9.2022.json`）；`source=user` 用你提供的课纲文件路径。

## 7. 各门含义（简）
- G1 schema 一致 / G2 覆盖完整 / G3 选择题有效性 / G4 难度分布 / G5 准确性(机判)
- G6 适龄 / G7 多样性去重 / G8 可追溯 / G9 课纲对齐（可选）
- 详见 skill `references/quality-gates.md`。
