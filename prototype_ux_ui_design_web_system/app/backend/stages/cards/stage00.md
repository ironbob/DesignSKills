# 阶段 0：影响分析（增量变更 · 任务卡）

已有工程续作的第一个阶段：读基线契约与新需求，产出**结构化、可程序消费**的影响分析。只分析，不重做任何设计。

## 输入（全部在当前 revision 工作区）

- `00-change-request.md`：新需求正文 + 变更说明（本次变更的唯一需求来源）
- 基线继承物：`09-spec.md`（交付契约）、`06-tokens.json`（token 数据源）、`07-hifi/`（高保真全屏×状态帧）、`03-屏幕与IA.md`（IA+屏幕盘点）、`02-流程草图.md`（任务流）、`01-需求消化.md`（历史决策台账）

## 产出

- `00-impact.md`：给人看的影响分析（变更摘要、逐页影响与理由、回归范围）
- `00-impact.json`：机器可读结构（**字段逐字对齐下方 schema，缺一不可**）：

```json
{
  "summary": "一句话变更摘要",
  "pages": {
    "added":   [{"page_id": "S6", "name": "成就页", "reason": "为何新增、挂在哪"}],
    "modified": [{"page_id": "S3", "name": "收尾小结", "level": "content", "reason": "改了什么"}],
    "removed": [{"page_id": "S9", "reason": "为何删除、入口与流程如何收口"}]
  },
  "flows": ["受影响的任务流（引用 02 的 F# 与一句说明）"],
  "navigation": ["受影响的导航（如底部导航新增入口）"],
  "states": ["受影响的状态（如 S3 新增同步失败态）"],
  "shared_change": {"tokens": false, "components": false},
  "regression_pages": ["S1", "S2"]
}
```

## 分级判定（每项修改必落一级；shared_change 命中时该级全局生效）

- `content`：文案/数据/必要状态，不动结构与视觉系统
- `component`：换件改配（组件族增改），设计系统要更新
- `layout`：结构改动（信息架构/布局模式变），必须回阶段 4
- `style`：token 层改动（色/字/距/圆角），改后受影响页面重出

## 硬规则

1. 修改/删除的页面必须在 `03-屏幕与IA.md` 盘点表中；新增页不得与基线冲突
2. 任何导航、流程、共享 token 或组件变更，`regression_pages` 必须列出关联页面与主流程页（回归验证但无需重做）
3. 重跑阶段由程序从本 JSON 确定性推导（分级→阶段映射），**不要自行编造执行计划**
4. 拿不准级别就保守取高一级（宁可多重跑，不可漏同步）

## 完成标志（L1 gate）

00-impact.json 可解析、三组页面结构合法、级别合法、页面存在性对得上基线、交叉变更带回归范围；00-impact.md 有实质内容。

## 工具化要点

- 决策类型=impact：gate 过后 revision 进入 impact_ready，**确认范围由用户拍板**（不自动重跑）
- 执行计划（stages_to_rerun/regression_pages 终值）由引擎 planner 算出并入 revisions.impact.plan——JSON 只需如实陈述影响事实
