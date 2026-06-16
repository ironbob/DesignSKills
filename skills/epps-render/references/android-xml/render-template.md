# Android XML 渲染规范：EPPS → layout.xml（预览级）

> 用途：指导把 `epps.json` 渲染成**每页一个 `layout/page_<id>.xml`** + 共享 `values/`（token 发射）。预览级：用 Material 标准组件（可在 Android Studio 预览面板渲染），**不接真实逻辑（无 `android:onClick`）**。
> 组件结构见 `component-mapping.md`；投影标记契约见 `projection.manifest.yaml`。交付前跑 `scripts/audit_projection.py`。

---

## 一、硬性原则

1. **每页一文件**：`layout/page_<page.id>.xml`（id 下划线小写）。
2. **严格投影**：每个 page 一个根布局；每个带 `epps:zoneId` 的容器对应一条 `density.zones[]`；不新增/遗漏 zone。
3. **示例数据同源**：文案从 `sample_state` 插值（`android:text` 用真实示例值）。
4. **token 单一源**：颜色/尺寸/字号从 `values/`（由主题预设发射）引用，不内联硬编码。
5. **预览级不接逻辑**：可点元素用 `epps:action` 标注目标，但**不写 `android:onClick`**（预览不执行）。

---

## 二、产物结构

```
android-xml/
├── values/
│   ├── colors.xml          # token: color.* → @color/epps_*
│   ├── dimens.xml          # token: shape/spacing/typography.size → @dimen/epps_*
│   └── themes.xml          # Material3 主题，引用 epps_* 颜色
└── layout/
    ├── page_<id>.xml       # 每页一个
    └── ...
```

---

## 三、Token 发射（values/）

`values/colors.xml`（由 `presets/<preset>.json` 的 `color.*` 发射）：
```xml
<resources>
  <color name="epps_primary">#165DFF</color>
  <color name="epps_on_primary">#FFFFFF</color>
  <color name="epps_secondary">#722ED1</color>
  <color name="epps_surface">#FFFFFF</color>
  <color name="epps_background">#EEF1F4</color>
  <color name="epps_on_surface">#1D2129</color>
  <color name="epps_on_surface_variant">#86909C</color>
  <color name="epps_outline">#E5E6EB</color>
  <color name="epps_success">#00B42A</color>
  <color name="epps_warning">#FF7D00</color>
  <color name="epps_danger">#F53F3F</color>
</resources>
```

`values/dimens.xml`（shape/spacing/字号）：
```xml
<resources>
  <dimen name="epps_shape_small">8dp</dimen>
  <dimen name="epps_shape_medium">12dp</dimen>
  <dimen name="epps_shape_large">16dp</dimen>
  <dimen name="epps_sp_xs">4dp</dimen><dimen name="epps_sp_sm">8dp</dimen>
  <dimen name="epps_sp_md">12dp</dimen><dimen name="epps_sp_lg">16dp</dimen><dimen name="epps_sp_xl">24dp</dimen>
  <dimen name="epps_text_headline">22sp</dimen>
  <dimen name="epps_text_title">17sp</dimen>
  <dimen name="epps_text_body">15sp</dimen>
  <dimen name="epps_text_label">13sp</dimen>
  <dimen name="epps_text_caption">11sp</dimen>
</resources>
```

`values/themes.xml`（Material3 主题，引用上述颜色）：
```xml
<resources>
  <style name="Theme.Epps" parent="Theme.Material3.DayNight.NoActionBar">
    <item name="colorPrimary">@color/epps_primary</item>
    <item name="colorOnPrimary">@color/epps_on_primary</item>
    <item name="colorSecondary">@color/epps_secondary</item>
    <item name="colorSurface">@color/epps_surface</item>
    <item name="android:colorBackground">@color/epps_background</item>
    <item name="colorOnSurface">@color/epps_on_surface</item>
    <item name="colorOutline">@color/epps_outline</item>
  </style>
</resources>
```

> 切换主题 = 换预设重发 `values/`；layout 结构不变。

---

## 四、投影标记契约（epps:* 命名空间，对账锚点）

布局根声明 `xmlns:epps="https://epps/render"`（框架忽略、脚本读取）：

| EPPS 概念 | XML 标记 |
|-----------|----------|
| 页面 | 根元素 `epps:pageId="<id>" epps:level="<level>" epps:type="<type>"` |
| zone | zone 根 `epps:zoneId="<zone.id>" epps:zoneKind="<zone.kind>"` |
| 辅助元素 | `epps:assistiveId="<id>" epps:assistiveKind="<kind>"` |
| 跳转目标 | `epps:action="target:<page.id>"` |
| 宿主锚点 | `epps:action="host:<host_anchor.id>"` |
| 行为 | `epps:action="behavior:<legal_behavior>"` |
| 主按钮 | primary `MaterialButton` 上加 `epps:priority="primary"`（每页 ≤ 1，对账 `PRIMARY.unique` 计数） |

> 这些 `epps:*` 属性对 Android 编译/预览无害；对账脚本按 `projection.manifest.yaml` 读取。

---

## 五、主次层级（核心）

按 `component-mapping.md` §二：
- `primary_action` → 唯一满宽 filled `MaterialButton`（`backgroundTint=@color/epps_primary`）。
- `secondary_actions`(`action_bar`) → `OutlinedButton`(`weight=1`)，水平排在 primary 之上。
- 行为 affordance → `epps:action="behavior:X"`，按 `placement` 只在一处。
- zone `priority` → 大卡/普通卡/弱化。

---

## 六、layout.xml 骨架示例（course_detail）

```xml
<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    xmlns:epps="https://epps/render"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="@color/epps_background"
    epps:pageId="course_detail" epps:level="2" epps:type="course_detail">

    <!-- top_bar -->
    <LinearLayout android:id="@+id/topbar"
        android:layout_width="match_parent" android:layout_height="wrap_content"
        android:orientation="horizontal" android:gravity="center_vertical"
        android:padding="16dp" android:background="@color/epps_surface"
        app:layout_constraintTop_toTopOf="parent">
        <ImageButton android:layout_width="wrap_content" android:layout_height="wrap_content"
            android:src="@android:drawable/ic_media_previous" android:background="?selectableItemBackgroundBorderless"
            epps:action="host:host_entry"/>
        <TextView android:layout_width="0dp" android:layout_height="wrap_content"
            android:layout_weight="1" android:layout_marginStart="12dp"
            android:text="@sample_state_lesson" android:textSize="@dimen/epps_text_title" android:textStyle="bold"
            android:textColor="@color/epps_on_surface"/>
    </LinearLayout>

    <!-- main_content: zones -->
    <ScrollView android:layout_width="match_parent" android:layout_height="0dp"
        app:layout_constraintTop_toBottomOf="@id/topbar" app:layout_constraintBottom_toTopOf="@id/action_bar">
        <LinearLayout android:layout_width="match_parent" android:layout_height="wrap_content"
            android:orientation="vertical" android:padding="16dp">

            <!-- zone: hero_card -->
            <com.google.android.material.card.MaterialCardView
                android:layout_width="match_parent" android:layout_height="wrap_content"
                android:layout_marginBottom="12dp" app:cardCornerRadius="@dimen/epps_shape_large"
                app:strokeWidth="0dp" app:cardBackgroundColor="@color/epps_secondary"
                epps:zoneId="today_task" epps:zoneKind="hero_card">
                <LinearLayout android:layout_width="match_parent" android:layout_height="wrap_content"
                    android:orientation="vertical" android:padding="18dp">
                    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
                        android:text="@sample_state_lesson" android:textSize="@dimen/epps_text_headline"
                        android:textStyle="bold" android:textColor="@color/epps_on_primary"/>
                    <TextView android:layout_width="wrap_content" android:layout_height="wrap_content"
                        android:text="@sample_state_progress_sub" android:textSize="@dimen/epps_text_label"
                        android:textColor="@color/epps_on_primary" android:alpha="0.85"/>
                </LinearLayout>
            </com.google.android.material.card.MaterialCardView>
        </LinearLayout>
    </ScrollView>

    <!-- action_bar -->
    <LinearLayout android:id="@+id/action_bar"
        android:layout_width="match_parent" android:layout_height="wrap_content"
        android:orientation="vertical" android:padding="12dp" android:background="@color/epps_surface"
        app:layout_constraintBottom_toBottomOf="parent">
        <com.google.android.material.button.MaterialButton
            android:layout_width="match_parent" android:layout_height="wrap_content"
            android:text="@primary_label" app:backgroundTint="@color/epps_primary"
            android:textColor="@color/epps_on_primary" app:cornerRadius="@dimen/epps_shape_medium"
            epps:action="target:learning" epps:priority="primary"/>
    </LinearLayout>
</androidx.constraintlayout.widget.ConstraintLayout>
```

> `@sample_state_*` / `@primary_label` 表示生成时从 `sample_state` / `primary_action.label` 插值出的真实文案（如 `android:text="开始学习"`）。

---

## 七、交付前对账

```bash
python skills/epps-render/scripts/audit_projection.py <epps.json> <render-dir> --platform xml
```

重点：每个 page 有且仅有一个带 `epps:pageId` 的根；zone 的 `(zoneId, zoneKind)` 序列与 spec 一致；所有 `epps:action` 目标落在已定义 page / host_anchor / legal_behavior；无 `android:onClick`（预览级）；文案已插值（无 `{{}}` 占位）。
