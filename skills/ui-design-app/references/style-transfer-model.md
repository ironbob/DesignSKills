# 风格迁移模型

> 大范围迁移的共同决策模型。目标是保留产品能力，用目标风格重新表达；不是复制来源 app 的业务结构。

## 1. 决策优先级

```text
目标功能与数据关系
> 可用性、无障碍、平台惯例
> 风格身份
> 条件性布局母题
> 装饰细节
```

不得为了相似度删除入口、改变数据关系、降低信息可读性、破坏键盘路径或强套来源布局。
来源 app 自身不适合目标平台的低对比、小热区或缺失语义也不迁移。

## 2. 五层迁移

| 层 | 内容 | 默认策略 |
| --- | --- | --- |
| L1 基础视觉 | 语义色、排版、几何、边框、阴影、材质 | 严格迁移；值引用 token |
| L2 空间节奏 | 控件高度、行距、间距、内容宽度、密度 | 保持气质，按数据量与可读性适配 |
| L3 组件语言 | 主次层级、选中、hover、pressed、open、disabled、focus、error | 严格迁移语义；尺寸可适配 |
| L4 交互气质 | 反馈方式、动效节奏、键盘提示、浮层行为 | 保留功能，迁移表现 |
| L5 布局母题 | 两栏、三栏、浮板、居中列、检查器 | 仅兼容且获确认时采用 |

L1-L4 决定风格身份。L5 不适用时标记 N/A，不扣风格分。

## 3. 规则分类

先用目标风格 `evidence.md` 锁定 source-version、platforms、representation 和 evidence-grade，再读取 `identity.md`，为每条规则使用以下分类：

- `invariant`：跨页面稳定、决定身份；迁移必须满足。
- `adaptive`：方向必须保持，具体值按平台、数据密度和目标功能调整。
- `archetype-bound`：只适用于兼容的页面类型；不兼容即 N/A。
- `source-specific`：来源 app 的功能或业务结构；默认禁止迁移。

遇到冲突时记录“保留了什么、放弃了什么、依据哪一级优先级”，不要静默折中。

## 4. 功能冻结

已有 app 开始视觉迁移前，记录并在完成后复测：

1. 页面、路由、导航层级和打开方式。
2. 主操作、次操作、危险操作及其可发现性。
3. 数据关系、排序、筛选、搜索、多选、批量和拖拽。
4. 默认、选中、编辑、加载、空、错误、禁用、离线和权限状态。
5. 快捷键、焦点顺序、Esc 链和浮层焦点归还。
6. 宽窗、窄窗、最小可用尺寸与现有主题能力。
7. 无障碍名称、语义角色和不只依赖颜色的状态表达。

允许为实现风格重构 DOM/CSS，但上述能力不得无授权改变。

## 5. 布局兼容判断

布局母题只有同时满足以下条件才可进入候选：

- 不减少核心入口或信息。
- 不改变用户完成主要任务的顺序。
- 能容纳真实数据密度和最长内容。
- 在目标最小窗口与输入方式下可用。
- 符合目标平台惯例。
- 用户已在 G1 单独确认结构变化。

否则保留原区域关系，只迁移 L1-L4。若局部兼容，可只采用内容列宽、面板表面、工具分组等局部母题。

## 6. 未覆盖组件推导

目标风格没有现成组件时，不跨风格复制。依次推导：

1. 确认组件的功能角色与完整状态机。
2. 从 `materials.md` 选择所在表面与层级。
3. 从 `components.md` 继承主次操作、选中、焦点、禁用和危险语义。
4. 从 `tokens.md` 组合排版、几何、间距、颜色和动效。
5. 用 `identity.md` 的 invariant 与反模式复查。
6. 把新模式记录为“derived”，实战稳定后再回写组件库。

来源精度标记：`observed` = 一手来源直接支持；`derived` = 多样本归纳或截图估算；`adapted` = 为目标可用性调整。判定与最低证据见 `evidence-standard.md`。

## 7. 视觉确认

已有 app 的 G1 优先并排呈现：

1. 当前界面或当前结构摘要。
2. 保留布局的目标风格版本（默认方案）。
3. 兼容时才提供布局增强版本，并明确变化与风险。

至少覆盖默认态与一个关键状态。高风险页面增加窄窗、长文本、加载/错误或高密度状态。

定制预览优先使用语义区域输入；`position` 只允许 top/left/main/right/bottom，`kind` 保留真实内容类型：

```json
{
  "style": "things",
  "preserveLayout": true,
  "viewport": {"width": 1280, "height": 800},
  "states": ["default", "error"],
  "regions": [
    {"id": "nav", "kind": "tree-navigation", "position": "left", "width": 240, "items": ["项目 A", "项目 B"]},
    {"id": "content", "kind": "data-table", "position": "main", "items": [{"label": "记录 1", "meta": "已同步", "selected": true}]},
    {"id": "inspector", "kind": "property-panel", "position": "right", "width": 280, "state": "error"}
  ]
}
```

旧的 `title/navigation/toolbar/rows` 输入继续用于通用 demo，不用于高风险迁移确认。

## 8. 双门验收

### 功能保持门（硬门）

导航、操作、数据关系、关键状态、键盘/焦点、响应式、主题能力和无障碍均不得无授权退化。
任一关键项失败即不能交付，不与视觉得分平均。

### 风格身份分（软评分）

使用 `score-style-transfer.py` 计算：

| 维度 | 通用默认权重 |
| --- | ---: |
| color | 15 |
| material | 15 |
| typography | 15 |
| geometry | 10 |
| spacing-density | 15 |
| component-states | 15 |
| motion-feedback | 10 |
| layout-motif | 5 |

具体风格以其 `identity.md` 权重为准。N/A 维度从分母移除。

- 90-100：风格身份稳定。
- 80-89：可交付，有少量漂移。
- 70-79：主要是主题感，组件或节奏不统一。
- <70：不算完成风格迁移。

评分必须附证据路径或说明；脚本只负责计算与验证结构，不代替设计判断。

输入 JSON 使用 `functional_gate` 八项硬门与 `dimensions`。维度可写数字，或写
`{"score": 88, "evidence": "截图/说明"}`；不适用项写
`{"applicable": false, "reason": "目标不是画布产品"}`。八项硬门键为：
`navigation`、`operations`、`data_relationships`、`critical_states`、`keyboard_focus`、
`responsive`、`theme_capability`、`accessibility`。
