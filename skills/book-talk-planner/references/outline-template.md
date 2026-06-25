# outline.md 渲染模板

> 把 `outline.json` 渲染成**人读**的选题提纲。`scripts/validate_render.py` 校验它，`validate_contract.py` 对账 json↔md。
> 渲染纪律：**每个 topic 的 `id` 必须在正文出现**（`### <id> · <title>`），让对账门能定位；角度/可信度不可省略。

## 模板

```markdown
---
book: <书名>
author: <作者>
input_mode: <title_only | title_plus_summary | full_text>
form: <series | single>
verdict: <worth_telling | marginal | thin>
viral_potential: <high | medium | low>
topic_count: <topics 数量>
generated_at: <YYYY-MM-DD>
---

# 《<书名>》讲书选题提纲

> 调性：<tone> · 输入：<input_mode> · 用户思路：<user_angle_direction>

## 一、可讲性判断

- 结论：<verdict 文述>（可讲点约 <talkable_points_estimate>，适合 <form>）
- 爆款潜力：<viral_potential> —— <viral_reason>

## 二、选题大纲

| ID | 选题 | 视角 | 形态 | 为什么值得讲 |
|----|------|------|------|--------------|
| T01 | <title> | <angle_name> | <video_form> | <why_worth_telling> |
| T02 | ... | ... | ... | ... |

## 三、讲解提纲

### T01 · <title>
- **视角**：<angle_name>（`<angle>`）
- **钩子方向**：
  - <hook_directions[0]>
  - <hook_directions[1]>
- **核心要点**：
  1. <key_points[0]>
  2. <key_points[1]>
  3. <key_points[2]>
- **金句方向**：<golden_line_direction>
- **形态**：<video_form>（single=1-3 分钟 / series=系列连载）
- **可信度**：
  - [<level>] <claim> —— <reason>
- **标题方向**：<title_directions>
- **封面方向**：<cover_direction>

### T02 · <title>
...（每个 topic 一段，结构同上）

## 四、说明
- 本提纲只到"选题 + 方向"，完整口播逐字稿由下游 skill 生成。
- 标 `[unverified]` / `[uncertain]` 的论断，成稿前需核实出处。
```

## 渲染纪律（对应 `validate_render.py`）

1. **frontmatter 齐全**：book / input_mode / form / verdict / viral_potential / topic_count 六项必填（门 `R-META`）。
2. **可讲性段**：`## 一、可讲性判断` 必须存在（门 `R-SEL`）。
3. **每个 topic id 出现**：每个 json topic 的 `id` 必须以 `### <id> ·` 在正文出现（门 `R-ID`，与 contract 门呼应）。
4. **角度覆盖**：正文出现的 distinct 视角 ≥ 3（门 `R-COVER`，与 json 的 `O-COVERAGE` 呼应）。
5. **可信度可见**：至少在有 credibility 条目的 topic 里出现 `[credible]`/`[uncertain]`/`[unverified]` 之一（门 `R-CRED`）。
6. **banned / placeholder 0**（门 `R-BANNED`）。
