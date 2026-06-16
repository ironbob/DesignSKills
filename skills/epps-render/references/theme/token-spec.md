# 主题 Token 契约（跨平台单一源）

> 用途：定义 epps-render 的视觉令牌（token）字段与单位，是**跨平台闭合契约**。所有预设主题（`presets/*.json`）按此结构填值；三平台发射器按此把 token 转成各平台资源。
> 改一处字段，必须同步：本文件 + `presets/*.json` + 三平台 `render-template.md` 的"token 发射"段 + `component-mapping.md` 引用的 token 名。

---

## 一、设计原则

- **单一源**：视觉只由一份预设 token 决定；三平台产物从同一份 token 发射，杜绝"HTML 蓝按钮、安卓红按钮"。
- **主次靠 token 表达**：`primary` 用 `color.primary` 填充 + 满宽；`secondary` 用描边（`color.outline`）+ `color.onSurface` 文字。层级即 token。
- **结构无关**：token 只管"长什么样"，不管"放哪个 zone"；zone 结构由 `epps.json` 决定。

---

## 二、Token 字段

### color（颜色，hex 字符串）

| 字段 | 语义 | 主次层级用途 |
|------|------|--------------|
| `primary` | 主行动点填充色 | `primary_action` 满宽按钮填充 |
| `onPrimary` | primary 上的文字/图标色 | 主按钮文字（通常 #fff） |
| `secondary` | 次要强调色 | 次要可视强调（如 hero 渐变端色、选中态） |
| `surface` | 卡片/容器底色 | `.zone`/卡片背景 |
| `background` | 页面底色 | 屏幕背景 |
| `onSurface` | 主文字色 | 正文/标题 |
| `onSurfaceVariant` | 次要文字色 | 副文案/`secondary` 按钮/`caption` |
| `outline` | 描边色 | 卡片描边/`secondary` 按钮描边/分隔线 |
| `success` | 成功/正向 | 对勾、掌握度"已掌握" |
| `warning` | 警告/进行中 | 进行中状态 |
| `danger` | 错误/危险 | 答错、删除 |

### typography（排版，size 单位 sp/px，weight 为字重数值）

| 字段 | size | weight | 用途 |
|------|------|--------|------|
| `headline` | 22 | 700 | hero 卡大标题/成绩数字 |
| `title` | 17 | 600 | 页面标题、卡片标题 |
| `body` | 15 | 400 | 正文、释义、例句 |
| `label` | 13 | 500 | 按钮、徽章、行标题 |
| `caption` | 11 | 400 | 辅助说明、音标、计数 |

> sp 与 px 在手机框（390×844）尺度下数值一致：HTML 直接用数值作 px；安卓 XML 用作 sp（文字）/ dp（间距）；Compose 用 `sp`（文字）/ `dp`（间距）。

### shape（圆角，dp）

| 字段 | 值 | 用途 |
|------|----|------|
| `small` | 8 | 徽章、小按钮 |
| `medium` | 12 | 主按钮、普通卡片 |
| `large` | 16 | hero 卡、大容器 |

### elevation（层级/阴影，dp）

| 字段 | 值 | 用途 |
|------|----|------|
| `level1` | 1 | 普通卡片 |
| `level2` | 3 | 悬浮/action-bar |
| `level3` | 8 | modal/弹层 |

### spacing（间距档位，dp）

| 字段 | 值 |
|------|----|
| `xs` | 4 |
| `sm` | 8 |
| `md` | 12 |
| `lg` | 16 |
| `xl` | 24 |

---

## 三、预设主题（presets/*.json）

| 预设 | 文件 | 定位 |
|------|------|------|
| 教育明亮 | `education-bright.json` | 默认；明亮、留白多，对齐 sample_data Arco-blue 调色板 |
| 教育暗色 | `education-dark.json` | 暗底护眼，同蓝系提亮 |
| 专业商务 | `professional.json` | 克制中性灰 + 单 teal 强调色 |

每文件顶层结构：

```json
{
  "name": "education-bright",
  "label": "教育明亮",
  "color":    { "primary": "#165dff", "onPrimary": "#ffffff", ... },
  "typography": { "headline": { "size": 22, "weight": 700 }, ... },
  "shape":    { "small": 8, "medium": 12, "large": 16 },
  "elevation":{ "level1": 1, "level2": 3, "level3": 8 },
  "spacing":  { "xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24 }
}
```

---

## 四、三平台 token 发射

| 平台 | 发射产物 | token → 资源映射 |
|------|----------|------------------|
| HTML | `:root` CSS 变量（内联进自包含 HTML） | `--primary`、`--surface`、`--shape-medium`(作 px) 等；`font-size`/`font-weight` 来自 typography |
| Android XML | `values/colors.xml` + `values/dimens.xml` + `values/themes.xml` | `color.primary` → `<color name="epps_primary">`；shape/spacing/elevation → `<dimen name="epps_shape_medium">`；typography.size → `<dimen>`(sp) |
| Android Compose | `theme/EppsTheme.kt` | `color.*` → `ColorScheme`；`typography.*` → `Typography`；`shape.*` → `Shapes`；spacing/elevation → 常量 `Dp` |

**切换主题** = 换一份 preset → 三平台 token 发射同步重生成，结构不变。
