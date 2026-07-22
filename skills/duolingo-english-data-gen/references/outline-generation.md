# 大纲生成规则（多邻国式英语课）

> 配合产出/确认大纲（Checklist 2/3a）、展开 content_list（3b）时加载。
> 三条杠杆（范围/数量/难度），但「年级×Bloom」换成「CEFR×curve_plan」；生成叶子单元是 **lesson**。

## 一、outline ≠ content_list

- **outline**（人审确认，语义层，每 CEFR 一文件 `outline/a1.json`）：Section→Unit→Lesson 树 + locked_targets + curve_plan + character_dialogue_hook + duoradio_episodes。几十行。
- **content_list**（机械展开，确定，千行）：每 lesson/每 radio 1 内容点，带 resolved curve_plan + locked_targets seed。id 稳定。

## 二、三条杠杆

### 范围（Range）—— 教什么
- 由**人审骨架**决定（像 seeds.py）：Section/Unit/Lesson 讲什么主题、对标哪个 CEFR。
- skill 不替用户定课纲；若用户无骨架，提保守的 A1 先行树（标 `source=generated`），YAGNI。

### 数量（Quantity）—— 多少
- 每个 Unit 含多少 Lesson；每 Lesson 多少题由 curve_plan.total（默认 15）决定。
- duoradio_episodes 按 CEFR 配若干。

### 难度（Difficulty）—— 多难
- 每课 `curve_plan`（见 difficulty-curve.md）：五 stage 有序、counts 和=total、结尾 end_on_easy。
- outline 课节点可**省略** curve_plan → 展开时继承 `config.curve_defaults[该课CEFR]`；也可显式覆盖（如口语专项课）。

## 三、outline 节点结构（见 data-types-and-schemas.md §二）

```
outline/<cefr>.json = {course, cefr, cast_ref, sections:[{id,title,order,units:[{
  id,title,order,theme, lessons:[{id,title,order,cefr,target_vocab,locked_targets,
  curve_plan?, character_dialogue_hook?}]}]}], duoradio_episodes:[{id,title,cefr,speakers,topic}]}
```

## 四、机械展开规则（3b，确定性，不再人审）

每 CEFR：
- 每个 outline lesson → 1 content_list 内容点（entity=lesson），带：
  - resolved `curve_plan`（显式或继承 curve_defaults[cefr]）
  - `seed`：{title, locked_targets, target_vocab, character_dialogue_hook}
  - `prompt_template` = "lesson.md"
- 每个 outline duoradio_episode → 1 内容点（entity=duoradio_episode），seed={title,speakers,topic}，prompt_template="duoradio.md"。
- id 稳定（= outline 节点 id）→ 改大纲只动变化条目。

## 五、id 约定

- lesson：`lesson-<cefr>-<unit序>-<课序>-<slug>`（如 `lesson-a1-1-1-hi`）。
- radio：`radio-<cefr>-<序>`（如 `radio-a1-1`）。
- exercise（生成时）：`ex-<lesson_id>-<slot序号>`。
- character：`c-<slug>`（如 `c-mia`），必须在 cast.json 注册。

## 六、人审重点

- locked_targets 是否锁定对了核心目标句/词（防漂移）。
- curve_plan 是否合理（默认通常够；口语专项课可显式加大 free_production）。
- character_dialogue_hook 的角色是否在 cast.json。
- duoradio 主题是否贴合 CEFR。
