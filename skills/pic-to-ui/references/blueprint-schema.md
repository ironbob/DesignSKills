# 契约 Schema：blueprint.json / delivery.json / assets-manifest.json

> 配合 pic-to-ui 的 Gate 1/2；Gate 3 见 `acceptance-schema.md`。本文是机器契约源，字段名、
> 枚举、必填项必须与脚本一致。
>
> 设计原则（来自记忆 `gate-scripts-for-skills`）：**模型显式声明优于推断覆盖**。脚本不反解析 native 代码，而是校验模型产出的显式声明——一张"应有"的蓝图 + 一张"已交付"的清单，两者对账。

## 三份产物的关系

| 文件 | 角色 | 谁产 | 门禁 |
|---|---|---|---|
| `text-ui-manifest.json` + `text-ui/*` | 每项截图/口述输入独立的文本空间图与用户确认 | 模型（第一阶段）+ 用户确认 | Gate 0 `validate_text_ui.py` |
| `blueprint.json` | **应有契约**——从已确认文本图和原始输入解析出的"这一屏该有什么" | 模型（解析阶段） | Gate 1 `validate_blueprint.py`（R1） |
| `delivery.json` | **已交付契约**——每个蓝图条目 → 代码锚点（交付/标红） | 模型（还原阶段，边还原边填） | Gate 2 `validate_delivery.py`（R2/R3/R4/R11） |
| `assets-manifest.json` | 图标/位图登记（来源、检索轨迹、许可） | 模型（图标阶段） | Gate 2 对账并检查真实素材 |

`report.md` 是人读渲染（自检报告 + 标红清单 + diff 备注），不是契约源。`repair` 模式另有 `repair-audit.json`，见 `repair-schema.md`；它记录现有实现差异和修复闭环，不替代这三份共同契约。

---

## 一、blueprint.json

从截图、口述或混合输入解析的"应有"契约。五大类齐全（缺任一类别 Gate 1 报 `BP.category.*` ERROR）。

### 顶层

| 字段 | 必填 | 说明 |
|---|---|---|
| `meta` | 是 | 模式/平台/框架/屏任务/范围，见下 |
| `structure_skeleton` | 是 | 布局骨架树（R4 来源），根节点须含 `node_id` |
| `entries[]` | 是 | 功能入口清单（R2 来源）；空时必须有 `empty_reasons.entries` |
| `icons[]` | 是 | 图标清单（R3/R11 来源）；空时必须有 `empty_reasons.icons` |
| `key_dimensions[]` | 是 | 关键尺寸比例（R5/P1 来源）；空时必须有 `empty_reasons.key_dimensions` |
| `states[]` | 是 | 交互态（R9 来源），每条须标 `source` |
| `bitmaps[]` | 否 | 位图（头像/配图/banner），默认 `handling: placeholder`（H1） |
| `empty_reasons` | 条件必填 | `entries/icons/key_dimensions/states` 任一为空时，以同名 key 写非空原因；禁止裸空数组通过 Gate 1 |

示例：纯展示屏可以写 `"entries": []`，但必须同时写
`"empty_reasons": {"entries": "参考截图为纯展示页，无可交互入口"}`。不存在的类别不能写入
`empty_reasons`，非空类别不需要写原因。

### meta

```json
"meta": {
  "mode": "create | repair",
  "platform": "iOS | Android",
  "framework": "SwiftUI | UIKit | Compose | Views | <工程实际>",
  "screen_job": "这一屏帮用户完成的一个当下任务（一句话）",
  "scope": "single_screen",
  "source_inputs": [
    {"id": "SHOT-01", "type": "screenshot"},
    {"id": "DESC-01", "type": "verbal"}
  ],
  "text_ui_guard": {
    "manifest": "text-ui-manifest.json",
    "result": "user_confirmed",
    "confirmed_input_ids": ["SHOT-01", "DESC-01"],
    "confirmation_evidence": "用户消息：两张文本图都确认"
  }
}
```

`mode` 表示任务类型：`create` 从截图创建目标屏；`repair` 修复已有但与截图不匹配的实现。

`framework` 按目标工程实际技术栈填（R10），**不强制** SwiftUI/Compose；工程技术栈不明时先与用户确认，不擅自假设。

`text_ui_guard` 必须回链 Gate 0 已确认 manifest。`source_inputs` 的 `{id,type}` 顺序必须与 manifest 的 `inputs[]` 一致，`confirmed_input_ids` 必须与 `inputs[].id` 一致；不能用自动确认或模型自评替代用户 evidence。口述中未指定的视觉细节不得声明为精确事实；应保留为 `inferred` 或 flag。Gate 1 的完整命令为：

```bash
python3 <skill-dir>/scripts/validate_blueprint.py blueprint.json \
  --text-ui-manifest text-ui-manifest.json --artifact-root <artifact-root>
```

### structure_skeleton（布局骨架树）

递归节点树。每个节点：

| 字段 | 必填 | 说明 |
|---|---|---|
| `node_id` | 是 | 稳定 id（如 `N1`、`N2-3`），Gate 2 据此对账 |
| `kind` | 是 | 结构语义：`screen` / `vstack` / `hstack` / `zstack` / `header` / `content_list` / `row` / `card` / `footer` / `tab_bar` / `media` / … |
| `children[]` | 否 | 子节点；无则省略或空数组 |

根节点必须含 `node_id`（Gate 1 `BP.structure.nonempty`）。**每个 node_id 都要在 `delivery.json` 的 `structure_nodes[]` 里交付或标红**（R4，Gate 2 `DLV.structure`）。

### entries[]（功能入口）

截图里**可触发某功能或跳转**的元素（按钮、Tab 项、菜单项、可点图标、链接）。

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | `ENTRY-##`（稳定 id，Gate 2 对账单位） |
| `kind` | 是 | `button` / `tab` / `menu_item` / `icon_button` / `link` |
| `semantic` | 是 | 这个入口做什么（语义，如"返回""立即支付""分享"） |
| `input_anchor` | 是 | 在输入中的位置（如 `top-left` / `bottom-bar:center` / `DESC-01:中心空状态`），可追溯回具体截图或口述 |

每条须四字段齐全。`entries` 为空时 Gate 1 默认失败；只有写出结构化空原因才可通过。

### icons[]

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | `ICON-##` |
| `semantic` | 是 | 图标表达的意思（如"返回箭头""搜索"）——语义对即可，不必像素一致（P2） |
| `input_anchor` | 是 | 输入中的位置 |
| `location` | 否 | 所在结构位置（如 `header`） |

`id/semantic/input_anchor` 齐全（Gate 1 `BP.icon.fields`）。图标**不得降级为文字/emoji**——这由 Gate 2 在 `delivery.json` 的 `asset.type` 上判定（R11）。

### key_dimensions[]（P1，比例级）

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | `DIM-##` |
| `what` | 是 | `spacing` / `fontsize` / `widget_size` |
| `ratio_note` | 是 | 比例描述（如"卡片间距约为正文字号 0.6x""头图高约为屏宽 0.45x"）——**比例对即可，不要求跨设备像素精确**（R5） |
| `reference_measurement` | 截图时强烈要求 | 基准截图测量：`{numerator:"主按钮高", numerator_px:44, denominator:"底栏高", denominator_px:72}`；口述没有像素基准时不伪造测量，改在 acceptance 中标 `unverified` |

不要求跨设备的绝对像素一致，但基准截图必须尽量量取像素作为比例证据。Gate 1 检查声明，Gate 2 映射真实代码锚点，Gate 3 必须对每个 `DIM-##` 记录 reference/after 比例、偏差、容差和证据；不能量取时标红，不得省略。

### states[]（交互态）

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | `STATE-##` |
| `kind` | 是 | `selected` / `disabled` / `empty` / `loading` / `error` / … |
| `source` | 是 | **`input` | `inferred`**（Gate 1 `BP.state.source` 强制） |
| `input_anchor` | source=input 时必填 | 该状态在截图或口述中的位置 |

来源标注不得混淆（R9）：来自确认输入的标 `input`，AI 推断的标 `inferred`（推断态默认进标红清单待确认）。

### bitmaps[]（位图，H1 默认占位）

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | `BMP-##` |
| `semantic` | 是 | 用途（如"用户头像""商品主图""运营 banner"） |
| `location` | 否 | 所在位置 |
| `handling` | 是 | 默认 `placeholder`（占位 + 标注待人工替换）；可选 `crop_inline` / `replicate`（见 H1，待用户确认） |

位图内容相似度不卡视觉硬门，但声明、handling、来源和许可必须通过 Gate 2 素材对账。

---

## 二、delivery.json

把蓝图条目映射到真实代码锚点。P0 必须 delivered，或具备用户明确批准的 waived；P1 可以
flagged。静默省略始终失败。

### meta.architecture_guard（编码路径门）

任何代码交付都必须回链已通过的 `change-assessment.json`。direct_ui 示例：

```json
"architecture_guard": {
  "mode": "direct_ui",
  "assessment": "change-assessment.json",
  "assessment_revision": 1,
  "implementation_owner": "pic-to-ui",
  "result": "passed",
  "validation_evidence": "change assessment exit 0; actual scope rechecked"
}
```

arch_first 示例：

```json
"meta": {
  "architecture_guard": {
    "mode": "arch_first",
    "assessment": "change-assessment.json",
    "assessment_revision": 2,
    "skill": "arch-first-code-gen",
    "invocation": "same_agent | subagent",
    "confirmation_mode": "user_confirmed | automatic_confirmed",
    "result": "passed",
    "design_contract": "docs/architecture/2026-08-09-checkout-design-contract.json",
    "architecture_doc": "docs/architecture/2026-08-09-checkout-arch.md",
    "validation_evidence": "validate_contract/doc/gate passed; semantic gaps recorded",
    "delegation_authorized": true
  }
}
```

- `mode` 必须与 assessment 的 `decision.path` 一致。
- direct_ui 必须声明 `implementation_owner=pic-to-ui`，不要求设计契约或架构文档。
- arch_first 的 `skill` 固定为 `arch-first-code-gen`，不能用自制 checklist 冒充。
- `invocation` 为 `same_agent` 或 `subagent`。
- `confirmation_mode` 遵循 arch-first 自己的确认规则；只有用户明确要求省略中间确认时才可用 `automatic_confirmed`。
- 两条路径都必须有 `assessment/assessment_revision/result=passed/validation_evidence`。
- 仅 arch_first 要求 `design_contract`、`architecture_doc`。
- `invocation=subagent` 时 `delegation_authorized` 必须为 true，且代码写入必须串行、单一所有者。
- Gate 2 必须传 `change-assessment.json` 与 `code-root`；仅 arch_first 路径要求设计契约和架构文档真实存在。

### 通用字段约定

每个条目（entries/icons/structure_nodes/dimensions/states 通用）：

| 字段 | 说明 |
|---|---|
| `<entity>_id` | 对应蓝图 id（`entry_id` / `icon_id` / `node_id` / `state_id`） |
| `status` | `delivered` \| `flagged` \| `waived` |
| `code_anchor` | `status=delivered` 时必填：`{file, widget}`（相对 code-root 的文件 + 控件/元素名） |
| `reason` | `status=flagged` 时必填：为什么没交付（进标红清单） |
| `asset` | 仅 icons：`{type, source, name}` |

Gate 2 的 `code-root` 为必填。`file` 必须真实存在且不能越出 code-root；`widget` 必须是文件中
可搜索到的稳定 symbol/identifier，而不是自然语言描述。

`delivery.meta.change_scope` 还必须列出本轮实际修改的所有生产代码文件，并回链 assessment revision：

```json
"change_scope": {
  "production_files": ["OrderDetailView.swift", "OrderDetailStyles.swift"],
  "assessment_revision": 1
}
```

文件数必须等于 assessment 的 `estimate.production_files`，所有 delivered code_anchor.file 必须在
此列表中。范围扩大时先修订 assessment，不能只扩充 delivery。

P0 的 entry/icon/structure 若为 `flagged` 会阻断交付。只有用户明确接受例外时才能写
`status: waived`，并同时提供：

```json
{"status":"waived","reason":"参考图标版权无法确认",
 "waiver":{"approved_by":"user","evidence":"用户在本轮明确接受不交付 ICON-03"}}
```

不得由模型自行推断或伪造 waiver。P1 的 dimension/state 可以 `flagged + reason`，不使用
`waived`。

### entries[]（R2，P0）

```json
{"entry_id": "ENTRY-03", "status": "delivered",
 "code_anchor": {"file": "OrderDetailView.swift", "widget": "PayButton"}}
```

每个 `ENTRY-##` 必须 delivered；flagged 会阻断最终交付，显式用户 waiver 除外。

### icons[]（R3 + R11，P0）

```json
{"icon_id": "ICON-02", "status": "delivered",
 "asset": {"type": "self_drawn", "source": "project", "name": "share.svg",
           "file": "Resources/Icons/share.svg", "code_reference": "shareIcon"},
 "code_anchor": {"file": "OrderDetailView.swift", "widget": "ShareButton"}}
```

| asset.type | 允许 | 说明 |
|---|---|---|
| `downloaded` | ✅ | 从指定网站下载；语义匹配即可，不必一模一样 |
| `self_drawn` | ✅ | Iconfont、Lucide、Material Symbols 全部无语义匹配时，自绘 SVG |
| `text` / `emoji` / `placeholder` / 空 | ❌ | **R11 禁止**——图标不得降级为文字。Gate 2 `DLV.icon.not_text` 报 ERROR |

每个 `ICON-##` 须有 asset 条目，`asset.type` ∈ {downloaded, self_drawn}。
所有类型必须含 `source/source_site/name/code_reference/search_trace`，且 `code_reference` 必须能在锚点代码中找到；两种类型都必须含 code-root 内真实存在的 `file`。`search_trace[]` 每项含 `{site, query, search_url, result}`：downloaded 至少记录其 `source_site` 的 `found`；self_drawn 必须记录 Iconfont、Lucide、Material Symbols 三站均为 `not_found`，并且文件只能是 `.svg`。

### structure_nodes[]（R4，P0）

```json
{"node_id": "N3", "status": "delivered",
 "code_anchor": {"file": "OrderDetailView.swift", "widget": "ContentList"}}
```

每个蓝图 `node_id` 必须 delivered；flagged 阻断，用户显式 waiver 除外。

### dimensions[]（R5，P1）

每个 `DIM-##` 必须在 `delivery.dimensions[]` 中 delivered + code_anchor，或 flagged + reason。
它把蓝图比例声明追到真实样式/token symbol；比例是否视觉正确仍由 Gate 3 的 diff 与自检判断。

### states[]（R9，P1）

```json
{"state_id": "STATE-02", "status": "flagged", "reason": "空状态截图未提供，已推断待确认"}
```

交互态的字段与锚点对账是结构硬门；视觉正确性为 P1。推断态默认 flagged 进标红清单。

### 标红清单 = 所有 `status: flagged` 的条目

跨类别把所有 `flagged` 条目汇总进 `report.md` 与 `acceptance.json`。P0 flagged 阻断交付；
P1 flagged 可通过结构门，但必须在 Gate 3 保留 reason/next_action，不能静默消失。

---

## 三、assets-manifest.json（图标/位图登记）

这是 Gate 2 的硬门输入，用于追溯每个图标的来源、许可、代码引用和真实文件，以及位图处理。

```json
{
  "icons": [
    {"icon_id": "ICON-01", "status": "delivered", "semantic": "返回箭头",
     "asset": {"type": "downloaded", "source": "Lucide", "source_site": "Lucide", "name": "arrow-left",
               "file": "Resources/Icons/arrow-left.svg", "code_reference": "arrow-left", "license": "ISC",
               "search_trace": [{"site":"Lucide", "query":"返回 arrow left", "search_url":"https://lucide.dev/icons/arrow-left", "result":"found"}]}},
    {"icon_id": "ICON-02", "semantic": "分享",
     "asset": {"type": "self_drawn", "source": "-", "name": "share.svg", "license": "项目自有"}}
  ],
  "bitmaps": [
    {"bitmap_id": "BMP-01", "semantic": "用户头像", "handling": "placeholder",
     "suggested_source": "用户上传/默认头像", "license": "not-applicable"}
  ]
}
```

Gate 2 同时读取本文件并执行 id、语义、类型、来源、许可、真实文件和 delivery 一致性对账。
许可字段必填或显式标“项目自有/待确认/not-applicable”，不可默写。

---

## 四、完整最小示例

最小 blueprint 仍须包含 meta、一个根结构节点，以及 entries/icons/key_dimensions/states 四个数组；
空数组必须有对应 empty_reasons。repair 模式另需生成非空差异审计。

## 五、id 规范

- 稳定、可追溯：`ENTRY-##` / `ICON-##` / `DIM-##` / `STATE-##` / `BMP-##` / 结构节点 `N##`
- 蓝图与 delivery 用同一 id 对账；id 不在蓝图中出现 → Gate 2 `DLV.dangling` ERROR
- 双端适配时，适配端沿用基准端 id 体系（对齐 entry/icon/structure），差异在标红清单说明
