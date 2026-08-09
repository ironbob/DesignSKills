# 共同还原工作流：截图目标解析 + 逐维防偷懒

> 本文适用于 create 和 repair 的共同目标解析与实现对账。repair 的现状审计、定点修复和回归另见 `repair-workflow.md`。

## 一、为什么截图比 figma 难（全程前提）

figma/HTML 自带结构化信息（图层、约束、组件实例、DOM 节点）；截图只是像素，AI 必须"看"出来，**偷懒空间巨大**——这正是四类痛点的根因。所以本 skill 的核心不是"生成代码"，而是**用 蓝图 + 清单 + 对账门 把"看"的过程强制做扎实**：

```
截图 ──解析──► blueprint.json（应有契约，过 Gate 1）
         ──创建或定点修复──► delivery.json（已交付契约，过 Gate 2）+ 视图代码 + assets-manifest
         ──验收──► acceptance.json（Gate 3）+ report.md + 真实 diff/降级声明
```

## 二、解析阶段：截图 → blueprint.json

**目标**：把截图"看"全，产出五类齐全的蓝图。这一步决定了后面还原的上限——漏看一个入口，后面就少一个。

逐类解析（顺序即填写顺序）：

1. **structure_skeleton**（先骨架）—— 先识别整体布局骨架（导航栏/内容区/底栏 → 内容区里是列表还是卡片网格 → 每个区块的嵌套）。写成节点树，每个节点给 `node_id` + `kind`。**先骨架后细节**，不一把梭。
2. **entries[]**（功能入口）—— 找全所有可触发/可跳转元素：按钮、Tab 项、菜单项、可点图标、链接。每个给 `ENTRY-##` + `kind` + `semantic` + `screenshot_anchor`。**这一类最易被偷懒省略**——务必穷举，宁可多标不可漏。
3. **icons[]** —— 找全所有图标，每个给 `ICON-##` + `semantic` + `screenshot_anchor`。图标和入口要分开记（一个可点图标既是 icon 也是 entry，两边都登记，对账时分别管）。
4. **key_dimensions[]** —— 提取关键尺寸的**比例**（间距/字号/控件尺寸的相对关系），写成 `ratio_note`。不要求像素值，比例对即可（R5/P1）。
5. **states[]** —— 识别交互态（选中/禁用/空/加载/错误）。来自截图的标 `source: screenshot` + anchor；截图没有、靠推断的标 `source: inferred`（默认进标红清单）。不得混淆（R9）。
6. **bitmaps[]**（位图）—— 头像/配图/banner，登记 `BMP-##` + `semantic`，默认 `handling: placeholder`（H1）。

### 截图锚点（screenshot_anchor）怎么写

要让条目能追溯回截图具体位置，便于人工核对与 diff：
- 区域描述：`top-left` / `bottom-bar:center` / `header:right` / `card-3:action`
- 或坐标：`(120, 480)`（截图像素，左上为原点）
- 多截图时，`meta.source_screenshots` 列序，anchor 可带截图序号如 `shot#2:bottom`

### 解析完跑 Gate 1

`python3 scripts/validate_blueprint.py blueprint.json`：五类齐全、字段完整、无占位符、state 有
source；任何空数组必须有 `empty_reasons.<category>`。不过就回解析阶段补，过门后才进入还原。

## 三、实施阶段：分步创建/修复 + 边实施边填 delivery.json

**顺序**：structure → 尺寸/样式 → 图标/位图 → 功能入口 → 交互态。每步实施完，立刻在
`delivery.json` 对应类别登记真实 `code_anchor`；P1 不确定项可 flagged。create 模式创建视图；
repair 模式只修改已审计差异的根因。不要写完全部代码再补声明。

### 第 1 步：结构骨架（R4，P0）

按 `structure_skeleton` 节点树搭代码骨架。每个 `node_id` 都要有对应实现，登记到 `delivery.structure_nodes[]`：
- 实现了 → `status: delivered` + `code_anchor{file, widget}`；
- 截图不清/有歧义，尽力做了但不确定 → `status: flagged` + `reason`。

**防"布局不一致"**：骨架节点必须真实交付；P0 flagged 阻断，用户显式 waiver 除外。

### 第 2 步：尺寸比例（R5，P1）

按 `key_dimensions` 的比例关系落实间距/字号/控件尺寸，并在 `delivery.dimensions[]` 映射到
真实 token/style symbol。比例对即可，不追求像素；视觉正确性由 diff + 自检判断。

### 第 3 步：图标（R3 + R11，P0）

对每个 `ICON-##`，按 ladder 处理（详见 `icon-sourcing.md`）：识别 → 平台系统资源 → 开源图标网络 → 自绘。登记到 `delivery.icons[]`：
- `asset.type` ∈ {`system`, `downloaded`, `self_drawn`} + `source` + `name` + `code_anchor`；
- 同步写 `assets-manifest.json`（含许可）。

**防"图标换成文字"（R11，P0 硬）**：`asset.type` 不得是 `text`/`emoji`/`placeholder`。Gate 2 `DLV.icon.not_text` 卡。平台系统图标资源合法；Unicode 字符不合法。**图标语义对即可，不必像素一致**（P2 顾问式）。

### 第 4 步：功能入口（R2，P0）

对每个 `ENTRY-##`，实现对应可交互控件，登记到 `delivery.entries[]`：`status: delivered` + `code_anchor{file, widget}`，或 flagged + reason。

**防"功能入口缺失"（R2，P0 硬）**：每个入口必须真实交付；flagged 不能绿灯。

### 第 5 步：交互态（R9，P1）

对每个 `STATE-##`：来自截图的照截图还原；推断的尽力做并标红。登记 `delivery.states[]`。
字段/锚点完整性是硬门，视觉正确性为 P1。

### 还原完跑 Gate 2

`python3 scripts/validate_delivery.py blueprint.json delivery.json assets-manifest.json code-root`：P0 必须
真实交付或具有用户明确 waiver；P1 可标红。脚本检查文件/widget、图标 code_reference、真实素材、
许可和三份契约一致性。不过就回实施阶段修复；不能靠自报 code_anchor 绿灯。

## 四、结构化验收（Gate 3）

1. **重新截图 diff**——能渲染则保存 reference/after/comparison 真实文件；不能则声明
   `unavailable + reason + unverified`。
2. **AI 七维自检**——覆盖 structure/entries/dimensions/style/icons/states/a11y，每项写判定与证据。
3. **测试与标红**——记录实际命令和结果；P0 flag 不得残留，P1/P2 写 reason/next_action。
4. 生成 `acceptance.json` 和对应 `report.md`，运行
   `python3 scripts/validate_acceptance.py acceptance.json delivery.json artifact-root`；repair 再传
   `--repair-audit repair-audit.json`。只有 Gate 3 exit 0 才交付。

## 五、逐维防偷懒速查

| 痛点 | 防法 | 卡在哪 |
|---|---|---|
| 布局不一致 | 先骨架后细节；节点真实交付 | Gate 2 `DLV.structure`（P0） |
| 功能入口缺失 | entries 穷举；P0 必须真实交付 | Gate 2 `DLV.entry`（P0） |
| 图标换成文字 | asset.type ∈ {system, downloaded, self_drawn} | Gate 2 `DLV.icon.not_text`（P0） |
| 尺寸不对 | 提取比例并映射到真实代码锚点 | Gate 2 + Gate 3 diff（P1） |
| 图标图案不准 | 语义对即可 | 顾问式自检（P2） |

## 六、双端适配（R6，基准端确认后）

1. 基准端先完整跑完上面全流程，过三道共同门 + 用户确认效果。
2. 适配端沿用 entry/icon/structure id，重画适配端 blueprint，重跑全部共同 Gate。
3. 框架差异（如 SwiftUI 的 VStack ↔ Compose 的 Column）在标红清单说明，不静默沿用基准端写法。

## 七、边界处理（R8 尽力做 + 标红）

截图不清 / 被截断（长列表）/ 有歧义时：
- **不停止**——尽力还原可见部分；
- **不静默**——不确定的条目 `flagged` + `reason`，进标红清单待人工核对；
- 不得用 TODO/占位悄悄跳过（Gate 1 `BP.placeholder` 会抓）。

## 八、反模式

| 反模式 | 正确做法 |
|---|---|
| 写完全部代码再补 delivery（易漏） | 边还原边登记 code_anchor |
| 入口/图标只实现"重要的"，省略"小的" | 穷举并真实交付；确需例外必须取得用户 waiver |
| 图标用文字/emoji 顶替 | 下载或自绘图标资源（R11） |
| 尺寸随便给个像素值 | 提取比例关系（R5） |
| 截图不清就跳过 | 尽力做 + flagged 标红（R8） |
| 推断的交互态当截图来源 | source 标 inferred（R9） |
| 一次性生成不校验就交付 | 过 Gate 1/2/3 才交付 |
| 没有 diff 却声称视觉 matched | Gate 3 记录 unavailable + unverified |
