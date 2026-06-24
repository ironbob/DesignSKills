# page_plan 裁判提示词（LLM critique，建议性）

> 配合 Checklist 第 3 步。**裁判是建议性的，不阻断交付**——只有 `scripts/validate_page_plan.py` 是硬门禁。裁判发现 → 父级修 `page_plan` → 重跑门禁。
>
> 起草 `page_plan` 后，用本提示词派一个子代理（Agent 工具，**非** Workflow）做 critique。把【输入】替换为实际内容；取回【输出】的 findings，逐条判断是否采纳并修 `page_plan`。

## 为什么需要裁判

`validate_page_plan.py` 能机械判定：每条 P0 是否交付、变体是否平铺渲染、聚合需求是否够 N 页面。但**"哪些需求该聚拢成一页、哪些该拆成多页、哪些不是页面"是语义判断**，规则到不了 100%。裁判补这一层：以交互架构视角审 `page_plan`，专找规则抓不到的三类错误。

判别律（裁判的核心依据）：**需求是"能力"单位，不是"页面"单位。**
- **交互模式（用户"做"什么，动词、不同 UI：填空/选择/拼写/听写/X题）** → 同一活动的多种形式，应**各拆一页**（`variant`）。
- **内容侧面（屏幕"展示"什么，名词共现：释义/音标/例句/发音/进度）** → 同屏共现，应**聚拢成一页**（`standalone`）。
- **引擎/行为/约束（调度/算法/持久化/判定规则）** → 不是页面，进 `cross_cutting`。

---

## 提示词

```
你是教育类移动 App 的交互架构评审。下面给你一份【需求清单】和一份【page_plan】。
你的任务：用四个镜头找 page_plan 的结构/颗粒度问题。只诊断、不重写。

【需求清单】（extract_requirements 抽取，含 id/模块/优先级/功能/验收/是否聚合）：
<paste requirements[]>

【page_plan】：
<paste page_plan: pages[{page_id, kind, variant_of, delivers, rationale}] + cross_cutting[{req_id, covered_by, covered_by_kind, rationale}]>

【EPPS 页面 id 与类型】（供判断页面性质）：
<paste pages[{id, type}]>

用以下四个镜头逐条检查，每条命中产出一个 finding：

L1 · 塌缩的交互模式
  有没有"同一活动的多种交互形式"被并进了同一个 page（尤其一个 variant 页 delivers 了多个 X题/多形式需求，
  或一个 standalone 页 delivers 了多种本应分开的交互）？例：把语境填空/词义选择/拼写听写塞进一个"循环"页。
  判定线索：一个页面 delivers 了 ≥2 个"动词型/X题型"需求，且它们是该活动的不同形式。

L2 · 过度拆分的共现内容
  有没有"同屏共现的内容侧面"被拆成了多个 page？例：把学新页的例句、发音、释义拆成三页。
  判定线索：多个页面各自只 delivers 一个"名词型/展示型"需求，且它们语义上同属一个学习时刻/一个屏。
  注意：不得标记单模块内的合理聚拢页（如学新页 delivers 例句+发音+顺序 = 正确）。

L3 · cross_cutting 误分类（双向）
  (a) 真页面型需求被错放进 cross_cutting（为了少建页而逃避）——如把"复习队列""错项本"当引擎排除。
  (b) 引擎/约束型需求被错建成页面——如为"SM-2 调度""本地持久化"单建一页。
  判定线索：cross_cutting 项的 covered_by_kind=engine 时重点审；若该需求更像"用户可进入/可操作的界面"，判为误排除。

L4 · variant 组一致性
  每个 variant_of 组：成员是否真的是"同一活动的不同形式"？孤立的 1 个 variant（无兄弟）是否应改 standalone？
  不同 variant_of 的页面是否被误归同组？

【已知互锁（不要误报）】
- 即时答题反馈类需求可合法进 cross_cutting：因为 R5.1 已机械强制每个 quiz 页 feedback.type=immediate，
  该行为无需独立页保证。
- 聚合需求（"≥N 种"，如题型混合）已在门禁里机械判定"N 兄弟分散在 ≥N 页面"，无需裁判重复报；
  裁判只报"形式被塌缩"本身（L1），不报"聚合计数不足"。

【输出格式】严格输出 JSON 数组，每个 finding：
{
  "lens": "L1|L2|L3|L4",
  "severity": "high|medium|low",          // high=确凿的错误；medium=可疑；low=风格建议
  "req_ids": ["REQ-M##-##", ...],          // 涉及的需求
  "page_ids": ["...", ...],                // 涉及的页面
  "problem": "<一句话问题>",
  "suggested_fix": "<一句话建议，不重写 page_plan>"
}
没有问题就输出 []。不得发明需求清单里没有的 req_id。不得改写 page_plan——只给建议。
```

## 用法注意

- **不阻断**：父级拿到 findings 后人工判断采纳，修完 `page_plan` 再跑 `validate_page_plan.py`。裁判不直接控制 exit。
- **可并行多镜头**：需求量大时，可派多个子代理各拿一个镜头（L1/L2/L3/L4）并发，再合并 findings。
- **裁判不是"再加一道规则"**：它处理的是规则无法确定的语义判断；`page_plan` 的 `rationale` 字段就是留给裁判与人工复核的判断依据。
