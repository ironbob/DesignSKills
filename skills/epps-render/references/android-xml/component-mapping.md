# Android XML 组件映射：14 zone.kind → Material Views

> 用途：把 14 种 `zone.kind` 映射到 Android 原生 layout.xml 的 Material 组件，并定义主次层级样式。与 `render-template.md`、`projection.manifest.yaml`、上游 `epps-schema.md` 的 zone.kind 枚举（14 种，闭合）同进同退。
> 14 种必须全覆盖。预览级：组件用标准 Material 组件（可在 Android Studio 预览渲染），不接真实逻辑（无 `android:onClick`）。

---

## 一、zone.kind → Material 组件

| kind | 根容器 | 内部组件 | 可点？ |
|------|--------|----------|--------|
| `hero_card` | `com.google.android.material.card.MaterialCardView`（渐变 drawable 背景） | `TextView`(headline) + `TextView`(副线) | 是（→ primary） |
| `quick_entries` | `androidx.gridlayout.widget.GridLayout` | `LinearLayout`(vertical) × N：`ImageView` + `TextView` | 是（→ target） |
| `badge_strip` | `LinearLayout`(horizontal) | `com.google.android.material.chip.Chip` × N | 否 |
| `word_card` | `MaterialCardView` | `TextView`(词头 headline) + `TextView`(音标+词性 caption) + `TextView`(释义 body) + `TextView`(例句 caption) | 含 affordance |
| `option_list` | `LinearLayout`(vertical) | `TextView`(题干) + `RadioButton`/`com.google.android.material.checkbox.MaterialCheckBox` × N + `TextView`(反馈) | 是（选） |
| `input_block` | `LinearLayout`(vertical) | `com.google.android.material.textfield.TextInputLayout`+`TextInputEditText` + `TextView`(反馈) | 是（输入） |
| `row_list` | `LinearLayout`(vertical) | `LinearLayout`(horizontal, clickable) × N：`TextView` + `ImageView`(chevron) | 是（→ target） |
| `chapter_tree` | `LinearLayout`(vertical) | `LinearLayout`(indented by `paddingStart`) × N + 状态标记 | 是（→ target） |
| `mastery_bar` | `LinearLayout`(horizontal) | 3 个加权 `View`（success/warning/outline 色） | 否 |
| `score_ring` | `FrameLayout` | `CircularProgressIndicator`(determinate) + 居中 `TextView`(分数) | 否 |
| `stat_grid` | `GridLayout` | `MaterialCardView`(数字+标签) × N | 否 |
| `progress_strip` | `LinearLayout`(vertical) | `LinearProgressIndicator`(determinate) + `TextView`(百分比) | 否 |
| `hint_block` | `TextView`（caption 样式） | — | 否 |
| `text_block` | `TextView` | — | 否 |

> 每个 zone 根容器必须带 `epps:zoneId` + `epps:zoneKind`（投影标记，见 `render-template.md`）。

---

## 二、主次层级 → Material 样式（主次分明）

| 权重 | 来源 | 组件 + style | 要点 |
|------|------|--------------|------|
| `primary` | `primary_action` | `MaterialButton`，`style="Widget.Material3.Button"`，`width:match_parent` | `app:backgroundTint="@color/epps_primary"`、文字 `@color/epps_on_primary`、满宽、唯一 |
| `secondary` | `secondary_actions[]`(`placement:action_bar`) | `MaterialButton`，`Widget.Material3.Button.OutlinedButton`，`layout_weight:1` | 描边 `@color/epps_outline`、降权；水平排列在 primary 之上 |
| `secondary`(inline) | `placement:content/inline` | `MaterialButton`，`Widget.Material3.Button.Icon`（`app:icon`） | 小尺寸图标，不抢 primary |
| `low` | 辅助/引导 | `TextView`/`Chip` 弱表达 | `@color/epps_on_surface_variant` |

**硬约束**：每页**只有一个** filled primary（标记 `epps:priority="primary"`；对账 `PRIMARY.unique` 计数 ≤ 1）；secondary 不得与 primary 等大并排；行为 affordance 按 `placement` 只在一处。

---

## 三、zone 内容优先级 → 视觉权重

| zone `priority` | 表达 |
|------------------|------|
| `primary` | `MaterialCardView` + 渐变 drawable / `elevation`，headline 字号 |
| `secondary` | 普通 `MaterialCardView`，`elevation:level1` |
| `low` | `TextView`(`@style/TextAppearance.Material3.BodySmall`) + variant 色 |

---

## 四、element_contract.surface → XML 承载

| surface | XML 承载 |
|---------|----------|
| `main_content` | zone 根容器（带 `epps:zoneId/zoneKind`） |
| `top_bar` | 顶部 `LinearLayout`（back + title） |
| `action_bar` | 底部 `LinearLayout`（sec-row + primary） |
| `badge` | `Chip` |
| `inline` | zone 内行内 `MaterialButton`(icon) |
| `coachmark`/`bottom_sheet`/`modal`/`toast`/`menu` | 预览级用占位 `FrameLayout`/`TextView` + `epps:assistiveId/Kind` 标注（不实现真实弹层逻辑） |

> `intent: guidance` 禁止作为主内容 zone；用 assistive 标注 + 弱表达。
