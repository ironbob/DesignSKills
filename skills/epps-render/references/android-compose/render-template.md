# Android Compose 渲染规范：EPPS → @Preview Composable（预览级）

> 用途：指导把 `epps.json` 渲染成**每页一个 `<Page>Page.kt`（含 `@Preview`）** + 共享 `theme/EppsTheme.kt`（token 发射）。预览级：用 Material3 标准 Composable（`@Preview` 可渲染），**不接真实逻辑（`onClick = {}`）**。
> 组件结构见 `component-mapping.md`；投影标记契约见 `projection.manifest.yaml`。交付前跑 `scripts/audit_projection.py`。

---

## 一、硬性原则

1. **每页一文件**：`<PageName>Page.kt`（页名 PascalCase + `Page`），内含 `@Composable` + `@Preview`。
2. **严格投影**：每个 page 一个 Preview 函数；每个 `// @epps zone` 注释对应一条 `density.zones[]`；不新增/遗漏。
3. **示例数据同源**：文案从 `sample_state` 插值（`Text("…")` 用真实示例值）。
4. **token 单一源**：颜色/字号/形状从 `EppsTheme`（由主题预设发射）引用，不内联硬编码。
5. **预览级不接逻辑**：可点元素用 `// @epps action` 标注目标，但 `onClick = {}`（空 lambda）。

---

## 二、产物结构

```
android-compose/
├── theme/
│   └── EppsTheme.kt        # token 发射：ColorScheme + Typography + Shapes + EppsTokens
└── <PageName>Page.kt       # 每页一个，含 @Preview
```

---

## 三、Token 发射（EppsTheme.kt）

由 `presets/<preset>.json` 发射成 Material3 `ColorScheme`/`Typography`/`Shapes` + 持有 spacing/elevation 的 `EppsTokens`：

```kotlin
package com.epps.render.theme

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

// color.*
private val EppsLight = lightColorScheme(
    primary = Color(0xFF165DFF), onPrimary = Color(0xFFFFFFFF),
    secondary = Color(0xFF722ED1), surface = Color(0xFFFFFFFF),
    background = Color(0xFFEEF1F4), onSurface = Color(0xFF1D2129),
    onSurfaceVariant = Color(0xFF86909C), outline = Color(0xFFE5E6EB),
    error = Color(0xFFF53F3F),
)

// typography.*
private val EppsTypography = Typography(
    headlineLarge = TypographyLine(22.sp, 700),
    titleLarge = TypographyLine(17.sp, 600),
    bodyLarge = TypographyLine(15.sp, 400),
    labelLarge = TypographyLine(13.sp, 500),
    bodySmall = TypographyLine(11.sp, 400),
)
private fun TypographyLine(size: androidx.compose.ui.text.TextUnit, weight: Int) =
    androidx.compose.ui.text.TextStyle(fontSize = size, fontWeight = androidx.compose.ui.text.FontWeight(weight))

// shape.*
private val EppsShapes = Shapes(
    small = RoundedCornerShape(8.dp), medium = RoundedCornerShape(12.dp), large = RoundedCornerShape(16.dp),
)

// spacing.* / elevation.*（非 Material3 内置，自定义 token）
object EppsTokens {
    val spacing = Spacing()
    val elevation = Elevation()
}
class Spacing { val xs = 4.dp; val sm = 8.dp; val md = 12.dp; val lg = 16.dp; val xl = 24.dp }
class Elevation { val level1 = 1.dp; val level2 = 3.dp; val level3 = 8.dp }

@Composable
fun EppsTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = EppsLight, typography = EppsTypography, shapes = EppsShapes, content = content)
}
```

> 切换主题 = 换预设重发 `EppsTheme.kt`（如 `EppsDark`）；Page 结构不变。

---

## 四、投影标记契约（// @epps 注释，对账锚点）

注释写在对应代码**上一行**（extractor 按行扫描，命名捕获组）：

| EPPS 概念 | 注释 |
|-----------|------|
| 页面 | `// @epps page=<id> level=<level> type=<type>`（置于 Preview 函数内最前） |
| zone | `// @epps zone id=<zone.id> kind=<zone.kind>`（置于 zone 容器上一行） |
| 辅助元素 | `// @epps assistive id=<id> kind=<kind>` |
| 跳转目标 | `// @epps action target=<page.id>` |
| 宿主锚点 | `// @epps action host=<host_anchor.id>` |
| 行为 | `// @epps action behavior=<legal_behavior>` |
| 主按钮 | `// @epps primary`（置于 primary `Button` 上一行；每页 ≤ 1，对账 `PRIMARY.unique` 计数） |

> extractor 按行扫描：遇到 `// @epps page=` 切换"当前页"，后续 zone/action 归属当前页。**page 注释必须先于该页的 zone 注释。**

---

## 五、主次层级（核心）

按 `component-mapping.md` §二：
- `primary_action` → 唯一满宽 `Button`（`Modifier.fillMaxWidth()`，`containerColor=primary`）。
- `secondary_actions`(`action_bar`) → `OutlinedButton`（`Modifier.weight(1f)`，`Row` 内），排在 primary 之上。
- 行为 affordance → `// @epps action behavior=X`，`onClick = {}`，按 `placement` 只在一处。
- zone `priority` → 大卡/普通卡/弱化。

---

## 六、`<Page>Page.kt` 骨架示例（course_detail）

```kotlin
package com.epps.render.pages

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.epps.render.theme.EppsTheme
import com.epps.render.theme.EppsTokens

@Composable
fun CourseDetailPage() {
    // @epps page=course_detail level=2 type=course_detail
    val s = EppsTokens.spacing
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Lesson 2 · 家庭成员") },
                navigationIcon = { /* @epps action host=host_entry */ Text("‹") }
            )
        },
        bottomBar = {
            Surface(tonalElevation = EppsTokens.elevation.level2) {
                Column(Modifier.padding(s.md)) {
                    // primary（唯一满宽）
                    // @epps primary
                    // @epps action target=learning
                    Button(
                        onClick = {},  // 预览级：空 lambda（目标用上一行注释标注供对账）
                        modifier = Modifier.fillMaxWidth(),
                        shape = MaterialTheme.shapes.medium
                    ) { Text("开始学习", fontWeight = FontWeight.SemiBold) }
                }
            }
        }
    ) { pad ->
        Column(
            Modifier.padding(pad).padding(horizontal = s.lg).verticalScroll(rememberScrollState())
        ) {
            // zone: hero_card
            // @epps zone id=today_task kind=hero_card
            Card(
                shape = MaterialTheme.shapes.large,
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondary),
                modifier = Modifier.fillMaxWidth().padding(bottom = s.md)
            ) {
                Column(Modifier.padding(s.xl)) {
                    Text("Lesson 2 · 家庭成员", style = MaterialTheme.typography.headlineLarge,
                        color = MaterialTheme.colorScheme.onSecondary, fontWeight = FontWeight.Bold)
                    Text("已完成 65%", style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSecondary)
                }
            }
        }
    }
}

@Preview(showBackground = true, widthDp = 390, heightDp = 844)
@Composable
private fun CourseDetailPagePreview() {
    EppsTheme { CourseDetailPage() }
}
```

> 文案（"开始学习"/"已完成 65%"）在生成时从 `sample_state`/`primary_action.label` 插值。`onClick = {}` = 预览级不接逻辑；目标用 `// @epps action` 注释标注供对账。

---

## 七、交付前对账

```bash
python skills/epps-render/scripts/audit_projection.py <epps.json> <render-dir> --platform compose
```

重点：每个 page 有 `// @epps page=` 且先于其 zone 注释；zone 的 `(id, kind)` 序列与 spec 一致；所有 `// @epps action` 目标落在已定义 page / host_anchor / legal_behavior；`onClick = {}`（预览级）；文案已插值（无 `{{}}` 占位）。
