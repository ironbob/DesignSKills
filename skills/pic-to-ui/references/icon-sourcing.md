# 图标与素材：图标 ladder + 获取网站 + 位图默认

> 配合 pic-to-ui 的图标维度（R3 + R11）。图标是"图标不对"痛点的核心，但用户已明确把图标拆成两件事：**P0 不能偷懒换成文字**（硬门），**P2 图案准确度要求降低、语义对即可**（顾问式）。本文给图标处理 ladder、图标获取网站候选、位图默认处理。

## 一、图标处理 ladder（R3）

对蓝图里每个 `ICON-##`，按顺序处理：

```
1. 识别 —— 从截图识别这个图标的语义（"返回箭头""搜索""心形收藏"……）
2. 系统资源 —— 优先复用平台系统图标 API/资源
3. 匹配下载 —— 系统库没有时，优先从 [Iconfont 图标库](https://www.iconfont.cn/collections/index) 找语义匹配的图标；也可从下列开源站点获取
4. 自绘 —— 下载不到，自绘 SVG/PNG
```

每步都要在 `delivery.json` 的 `icons[]` 登记：

| asset.type | 何时用 | 登记示例 |
|---|---|---|
| `system` | 使用平台系统图标 API/资源 | `{type:"system", source:"SF Symbols", name:"chevron.left", code_reference:"chevron.left"}` |
| `downloaded` | 在图标网络找到语义匹配的 | `{type:"downloaded", source:"Lucide", name:"arrow-left", file:"Resources/arrow-left.svg", code_reference:"arrowLeft"}` |
| `self_drawn` | 找不到，自绘 | `{type:"self_drawn", source:"project", name:"share.svg", file:"Resources/share.svg", code_reference:"shareIcon"}` |

**禁止**（R11，Gate 2 `DLV.icon.not_text` 硬卡）：`text` / `emoji` / `placeholder` / 空。截图里的图标**必须还原为真实图标资源**，不得用文字或 emoji 顶替。`system` 指平台提供的图标资源，不是 Unicode 字符。

Gate 2 会检查 `code_reference` 确实出现在锚点代码中；downloaded/self_drawn 的 `file` 必须在
code-root 内真实存在，并与 `assets-manifest.json` 的 type/source/name/file/code_reference 一致。

## 二、图标获取网站（U2，确切集合可配置）

网站首选为 [Iconfont 图标库](https://www.iconfont.cn/collections/index)，适合按中文语义搜索并直接获取 SVG/PNG 或使用项目图标库。Iconfont 中的图标可能使用不同授权；下载或引入前必须核对**具体图标/项目**的许可，不能将其一概视为开源。

其他容易获取的开源备选网站（按平台匹配度选择）：

| 网站 | 平台适配 | 许可 | 说明 |
|---|---|---|---|
| [Google Material Symbols](https://fonts.google.com/icons) | Android（Compose/Views） | Apache 2.0 | Android 首选，可直接搜索和下载 |
| [Lucide](https://lucide.dev/icons/) | 跨平台 | ISC | 通用、风格统一、覆盖广，提供 SVG 和各框架包 |
| [Tabler Icons](https://tabler.io/icons) | 跨平台 | MIT | 图标量大，支持 SVG 复制/下载 |
| [Heroicons](https://heroicons.com/) | Web / 跨平台 | MIT | 轮廓、实心和 mini 三套风格，易直接复制 SVG |
| [Iconify](https://icon-sets.iconify.design/) | 跨平台（聚合） | 各图标集许可不同 | 可检索大量图标集；使用前核对所选图标集许可 |
| [Feather](https://feathericons.com/) | 跨平台 | MIT | 简洁线性图标，可直接复制 SVG |

**选择原则**：
- iOS 工程优先 SF Symbols；Android 工程优先 Material Symbols——与平台观感一致，且随系统主题（深色模式/动态配色）自适应。
- 系统库不能覆盖时，先在 Iconfont 获取；若需明确的开源许可证、统一风格或框架包，使用 Lucide、Tabler、Heroicons、Feather 或 Material Symbols。Iconify 只作为聚合检索入口。
- **语义匹配即可，不要求视觉像素一致**（P2）：截图是"返回箭头"，下载一个 chevron.left / arrow_back 即可，不必长得一模一样。
- 找不到任何语义匹配的 → 自绘 SVG/PNG（asset.type: self_drawn）。

**许可必须登记**：在 `assets-manifest.json` 每个图标写 `license`（如 "Apache 2.0" / "Apple SF Symbols License" / "项目自有"）。各网络许可不同，不可默写；自绘的标"项目自有"。

> 确切的图标获取方式（离线包/下载脚本/直接复制 SVG）属未决（U2），留技术设计；首版用上述网站 + 手动获取。

## 三、位图素材默认处理（H1）

截图里的**位图**（头像、配图、banner、商品图等）与图标不同——位图难以从截图可靠提取（糊/版权），默认：

| handling | 说明 |
|---|---|
| **`placeholder`（默认）** | 用占位图，在 `assets-manifest.json` 标注 位置/用途/建议来源，待人工替换 |
| `crop_inline`（备选） | 从截图裁出位图直接内联——仅当用户明确要求，注意可能糊/有版权 |
| `replicate`（备选） | 用代码绘制或找相似资源复刻——成本高，仅当用户明确要求 |

位图内容相似度不作为视觉硬门，但 bitmap 声明、handling、来源与许可必须通过 Gate 2。
默认 placeholder 是因为图标有“语义对即可”的判据，具体照片没有合理的近似；占位并标注待替换最诚实。

> 位图默认 placeholder 是否认可，属未验证假设 H1，待用户确认。

## 四、a11y 轻量兼顾（默认假设 H4）

还原图标/控件时轻量兼顾无障碍：
- 图标给语义化标签（iOS `accessibilityLabel` / Compose `contentDescription`）；
- 可点区域 ≥ 44×44pt（iOS）/ 48×48dp（Android）；
- 不只靠颜色传达状态（如禁用态同时降透明度 + 灰度）。

不做完整 a11y 审计（H4 默认假设），但避免明显可访问性退化。

## 五、反模式

| 反模式 | 正确做法 |
|---|---|
| 图标用文字/emoji 顶替 | 下载或自绘（R11 硬门） |
| 凭感觉塞个"差不多"的图标不登记 | 每图标登记 asset（type/source/name）+ 许可 |
| 位图直接内联截图裁图（糊/版权） | 默认 placeholder + 标注，待人工替换 |
| 不标许可就用开源图标 | assets-manifest 每图标写 license |
| 强求图标与截图像素一致 | 语义对即可（P2），平台系统库优先 |
