# 平台注册表：epps-render 支持的平台

> 用途：登记本 skill 支持的渲染平台、各平台的投影策略，以及**如何新增一个平台**（manifest 数据驱动，零 Python 改动）。
> 与 `scripts/audit_projection.py` 的抽取器策略一一对应。

---

## 一、已支持平台

| 平台 | 目录 | parse 策略 | 产物形态 | 投影标记 |
|------|------|-----------|----------|----------|
| HTML | `references/html/` | `dom_html` | 自包含可点击多屏 `prototype.html` | `data-*` 属性 |
| Android XML | `references/android-xml/` | `dom_xml` | 每页 `layout/page_<id>.xml` + 共享 `values/` | `epps:*` 命名空间属性 |
| Android Compose | `references/android-compose/` | `text_regex` | 每页 `<Page>Page.kt`（`@Preview`）+ `theme/EppsTheme.kt` | `// @epps ...` 结构化注释 |

每平台三件套（缺一不可）：

1. `render-template.md` —— 如何按 spec 写产物 + 投影标记契约。
2. `component-mapping.md` —— 14 `zone.kind` → 该平台原生组件 + 主次层级映射。
3. `projection.manifest.yaml` —— 标记怎么读（对账脚本的输入）。

---

## 二、parse 策略（通用抽取器内置，覆盖近未来平台）

`audit_projection.py` 的通用抽取器只认这 3 种 `parse` 策略：

| `parse` | 适用 | 读法 |
|---------|------|------|
| `dom_html` | HTML / 类 HTML | CSS 风格选择器 + 属性名（html.parser 解析） |
| `dom_xml` | XML（Android layout、SVG、XAML…） | namespace + 属性名（xml.etree 解析） |
| `text_regex` | 源码型（Kotlin/Swift/Dart/JSX…） | 命名捕获组正则（按行扫描） |

> iOS SwiftUI、Flutter Dart 多半属源码型，可直接复用 `text_regex`；Web 类标记语言用 `dom_html`/`dom_xml`。

---

## 三、新增一个平台（零 Python 改动）

新增平台（如 iOS SwiftUI）的步骤——**核心（解析/主题/对账比较）不动，抽取器代码不动**：

1. **新建目录** `references/<平台>/`。
2. **写 `render-template.md`**：该平台如何按 `epps.json` 写产物；定义投影标记写法（建议复用现有标记语义：page/zone/assistive/action{target|host|behavior}）。
3. **写 `component-mapping.md`**：14 `zone.kind` → 该平台组件表 + 主次层级样式映射。
4. **写 `projection.manifest.yaml`**：声明标记怎么读。文本型平台多半复用 `text_regex` 策略，只填 pattern：
   ```yaml
   parse: text_regex
   page:      { pattern: '<你的 page 标记正则，命名组 id/level/type>' }
   zone:      { pattern: '<zone 标记，命名组 id/kind>' }
   assistive: { pattern: '<assistive 标记，命名组 id/kind>' }
   action:    { pattern: '<action 标记，命名组 kind/target|host|behavior 与 value>' }
   ```
5. **在本表（§一）登记一行**。
6. **在 `SKILL.md` 的"已支持平台"描述里加一项**。

完成 1–6，新平台即可被 `audit_projection.py --platform <平台>` 对账，且渲染时按其三件套生成。

> 唯一需要改 Python 的情形：新平台标记形态 `dom_html`/`dom_xml`/`text_regex` 三策略都套不上。属罕见；此时给通用抽取器加一个 `parse` 策略（仅此一处改动，比较核心仍复用）。
