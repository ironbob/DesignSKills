# Android Compose 组件映射：14 zone.kind → Material3 Composable

> 用途：把 14 种 `zone.kind` 映射到 Jetpack Compose（Material3）Composable，并定义主次层级。与 `render-template.md`、`projection.manifest.yaml`、上游 `epps-schema.md` 的 zone.kind 枚举（14 种，闭合）同进同退。
> 14 种必须全覆盖。预览级：用 Material3 标准 Composable（`@Preview` 可渲染），不接真实逻辑（`onClick = {}`）。

---

## 一、zone.kind → Material3 Composable

| kind | 容器 | 内部 Composable | 可点？ |
|------|------|------------------|--------|
| `hero_card` | `Card` + `Box`(渐变 `Brush`) | `Text`(headline) + `Text`(副线) | 是（→ primary） |
| `quick_entries` | `FlowRow` | `Column` × N：`Icon` + `Text`（`clickable`） | 是（→ target） |
| `badge_strip` | `Row` | `AssistChip` × N | 否 |
| `word_card` | `Card` + `Column` | `Text`(词头 headline) + `Text`(音标+词性 caption) + `Text`(释义 body) + `Text`(例句 caption) | 含 affordance |
| `option_list` | `Column` | `Text`(题干) + `RadioButton`/`Checkbox` × N + `Text`(反馈) | 是（选） |
| `input_block` | `Column` | `OutlinedTextField` + `Text`(反馈) | 是（输入） |
| `row_list` | `Column` | `ListItem` × N（`Modifier.clickable`） | 是（→ target） |
| `chapter_tree` | `Column` | `ListItem`(按层级 `paddingStart`) × N + 状态标记 | 是（→ target） |
| `mastery_bar` | `Row` | 3 个加权 `Box`（success/warning/outline 色，`Modifier.weight`） | 否 |
| `score_ring` | `Box` | `CircularProgressIndicator`(determinate) + 居中 `Text`(分数) | 否 |
| `stat_grid` | `Column` 或 `LazyVerticalGrid` | `Card`(数字+标签) × N | 否 |
| `progress_strip` | `Column` | `LinearProgressIndicator`(determinate) + `Text`(百分比) | 否 |
| `hint_block` | `Text`（`bodySmall`） | — | 否 |
| `text_block` | `Text` | — | 否 |

> 每个 zone 容器**上方**必须有 `// @epps zone id=<zone.id> kind=<zone.kind>` 注释（投影标记，见 `render-template.md`）。

---

## 二、主次层级 → Material3 样式（主次分明）

| 权重 | 来源 | Composable | 要点 |
|------|------|-----------|------|
| `primary` | `primary_action` | `Button`（filled），`Modifier.fillMaxWidth()` | `containerColor = primary`、`contentColor = onPrimary`、满宽、唯一 |
| `secondary` | `secondary_actions[]`(`action_bar`) | `OutlinedButton`，`Modifier.weight(1f)`（`Row` 内） | 描边降权；水平排在 primary 之上 |
| `secondary`(inline) | `placement:content/inline` | `IconButton` + `Icon`，或 `TextButton` | 小尺寸，不抢 primary |
| `low` | 辅助/引导 | `Text`/`AssistChip` 弱表达 | `onSurfaceVariant` 色 |

**硬约束**：每页**只有一个** filled primary `Button`（标记 `// @epps primary`；对账 `PRIMARY.unique` 计数 ≤ 1）；secondary 不得与 primary 等大并排；行为 affordance 按 `placement` 只在一处。

---

## 三、zone 内容优先级 → 视觉权重

| zone `priority` | 表达 |
|------------------|------|
| `primary` | `Card` + 渐变 `Brush` / `elevation`，`headline` 字号 |
| `secondary` | 普通 `Card`，`elevation = level1` |
| `low` | `Text`(`MaterialTheme.typography.bodySmall`) + variant 色 |

---

## 四、element_contract.surface → Compose 承载

| surface | Compose 承载 |
|---------|--------------|
| `main_content` | zone 容器（前缀 `// @epps zone` 注释） |
| `top_bar` | `TopAppBar` / 顶部 `Row`（back + title） |
| `action_bar` | 底部 `Column`（`Row`(secondary) + `Button`(primary)） |
| `badge` | `AssistChip` |
| `inline` | zone 内 `IconButton`/`TextButton` |
| `coachmark`/`bottom_sheet`/`modal`/`toast`/`menu` | 预览级用占位 `Card`/`Text` + `// @epps assistive` 注释（不实现真实弹层） |

> `intent: guidance` 禁止作为主内容 zone；用 assistive 注释 + 弱表达。
