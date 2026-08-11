# 图标与素材：语义等价 + 指定站点检索 + SVG 兜底

> 配合 pic-to-ui 的图标维度（R3 + R11）。图标的验收目标是**语义与可表达性**，不是复刻截图里的每一条路径或像素；但图标来源和“为什么自绘”必须可追溯。

## 一、不可变规则

- 截图图标可以使用**语义等价**的图标：例如截图是返回箭头，`arrow-left`、`chevron-left`、`arrow_back` 都可接受；不要求外形一模一样。
- 不得用文字、emoji、Unicode 字符或 placeholder 代替图标。
- 只能从下列指定网站检索和下载：**Iconfont、Lucide、Material Symbols**。不要改用未列网站、搜索引擎图片或临时网页图标。
- 只有三个指定网站都没有可表达该语义的图标时，才允许自行生成**SVG**；不可因“和截图长得不够像”直接自绘。
- 每个图标在 `delivery.json` 与 `assets-manifest.json` 中保留完全一致的 `search_trace[]`；Gate 2 校验它。

## 二、固定检索 ladder

对每个 `ICON-##`，依次执行并记录：

1. 用截图语义检索 [Iconfont](https://www.iconfont.cn/collections/index)，优先中文和常见功能词。
2. 若未找到可表达的图标，检索 [Lucide](https://lucide.dev/icons/)；优先统一的跨平台线性风格。
3. 若仍未找到，检索 [Material Symbols](https://fonts.google.com/icons)；其语义名和填充/圆角变体通常足够覆盖 UI 控件。
4. 任一站点找到语义等价图标后，下载/导出 SVG 并结束 ladder；不要为了图案近似程度继续搜或自绘。
5. 三站均 `not_found` 后，才生成最小、自包含的 SVG，并让 `source_site` 为 `generated`。

检索不是口头动作。每次搜索写入：

```json
{"site":"Lucide", "query":"返回 arrow left", "search_url":"https://lucide.dev/icons/arrow-left", "result":"found"}
```

`result` 只能是 `found|not_found`。下载时只需记录命中站点；自绘时须包含三站的 `not_found`。选择结果要以“能否表达截图语义”为准，**不能以是否像截图原图为准**。

## 三、资产登记

下载图标：

```json
{"type":"downloaded", "source":"Lucide", "source_site":"Lucide", "name":"arrow-left",
 "file":"Resources/Icons/arrow-left.svg", "code_reference":"arrowLeft",
 "license":"ISC",
 "search_trace":[{"site":"Lucide", "query":"返回 arrow left",
                  "search_url":"https://lucide.dev/icons/arrow-left", "result":"found"}]}
```

自绘 SVG：

```json
{"type":"self_drawn", "source":"project", "source_site":"generated", "name":"custom-action.svg",
 "file":"Resources/Icons/custom-action.svg", "code_reference":"customAction",
 "license":"项目自有",
 "search_trace":[
   {"site":"Iconfont", "query":"自定义动作", "search_url":"https://www.iconfont.cn/collections/index", "result":"not_found"},
   {"site":"Lucide", "query":"custom action", "search_url":"https://lucide.dev/icons/", "result":"not_found"},
   {"site":"Material Symbols", "query":"custom action", "search_url":"https://fonts.google.com/icons", "result":"not_found"}
 ]}
```

下载图标要核对实际图标/项目许可并写 `license`；自绘写“项目自有”。`source_site`、`file`、`code_reference`、`search_trace` 必须在 delivery 与 manifest 对账一致。

## 四、位图素材默认处理

截图里的头像、配图、banner 等位图与图标不同：默认使用 `placeholder` 并在 `assets-manifest.json` 写明用途、建议来源和许可。用户明确要求时才裁图或复刻；不要把位图默认策略套到图标上。

## 五、反模式

| 反模式 | 正确做法 |
|---|---|
| 强求图标与截图像素一致 | 选语义等价图标，保持同屏风格协调 |
| 凭感觉自绘一个图标 | 先按 Iconfont → Lucide → Material Symbols 留下检索证据 |
| 一个网站没搜到就自绘 | 三个指定网站全部 `not_found` 才允许自绘 SVG |
| 用系统字符、文字或 emoji 充当图标 | 使用下载 SVG 或合规自绘 SVG |
| 找到图标却不记录来源/许可 | delivery 与 manifest 同步登记检索轨迹、文件和 license |
