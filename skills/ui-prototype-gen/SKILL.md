---
name: ui-prototype-gen
description: "Trigger only when the user explicitly asks to use this skill by name: `$ui-prototype-gen`, `ui-prototype-gen`, or a namespaced form ending in `:ui-prototype-gen`. Do not trigger from task similarity, prototype, UI, or requirements keywords, or inferred intent. Runs the nine-stage expert design workflow (understand → flows → IA → key-screen wireframes → style direction → design system → hi-fi → interaction spec & crit → handoff spec), one confirmed stage at a time, producing validated HTML prototypes and a self-contained coding spec."
---

# ui-prototype-gen：九阶段专家设计工作流

## 目的

把一份需求文档变成**可点击原型 + 自包含设计规格**。工作法来自人类交互/UI 设计师的真实实践（需求消化→流程草图→IA→关键屏低保真→风格→设计系统→高保真→交互说明与评审→交付），经真实项目完整走通校准——**不是**"把需求丢给 AI 一次性生成全部页面"。

四个与生俱来的约束：

1. **按模式确认**（step/auto 两档）：
   - **step（默认）**：每阶段交付→人审/拍板→记台账→才进下一阶段；
   - **auto**：事实类阶段（2/3/6/7/9）由双层 gate 放行自动推进；答案类（1）、品味类（4/5）、豁免类（8）**任何模式必停人工**。
   两档的放行判据相同：L1 确定性 gate 全绿 + L2 AI 评审 🔴=0 + 重试 ≤2。
2. **中间产物是消耗品，交付物是契约**：`09-spec.md` + `06-tokens.json` + `07-hifi/` 是契约；其余过程文件可扔可改。
3. **一致性来自共享约束**（token/组件/画布规则），不来自整批一起生成。
4. **生成与评审分离**：L2 评审用独立判据卡（`references/rubric-0N.md`）+ fresh context，只出 findings（🔴/🟡+证据），verdict 由编排引擎数出（🔴=0），评审器无自由裁量权、不许改产物。

## 工作区契约（磁盘是唯一真相源）

```
<workspace>/
  00-requirement.md            # 输入：需求文档
  01-需求消化.md               # memo + ★决策台账（全流程锚点，所有拍板追加于此）
  02-流程草图.md               # Mermaid 任务流
  03-屏幕与IA.md               # IA + 屏幕盘点 + 闭环检查 + 关键屏提名
  04-wireframes/               # 关键屏灰框（×2 变体）+ index.html
  05-style-tiles/              # 三方向 tile + index.html
  06-tokens.json               # ★token 数据源（机器可读）
  06-design-system.html        # 组件规范样张（给人看）
  07-hifi/                     # 全部屏 × 状态帧 + index.html
  08-交互说明.md               # 模式×状态矩阵 + 转场标注
  08-prototype.html            # 主流程可点原型
  08-findings.md               # crit 审计记录
  09-spec.md                   # ★交付规格（编码智能体消费）
```

## 阶段总表

| # | 阶段 | 产物 | 人工决策点 | 决策类别 | auto 可过? | gate |
|---|---|---|---|---|---|---|
| 1 | 需求消化 | 01：job stories+问题清单+成功标准+台账骨架 | **答阻塞问题** | 答案类 | ✗ | L1+L2 |
| 2 | 流程草图 | 02：Mermaid F1–F4 | 审走向+拍 P2-x | 事实类 | ✓ | L1+L2 |
| 3 | 屏幕与 IA | 03：IA+盘点表+闭环 | 认屏幕清单/关键屏 | 事实类 | ✓ | L1+L2 |
| 4 | 关键屏低保真 | 04-wireframes ×2 变体 | **挑变体** | 品味类 | ✗ | L1+L2 |
| 5 | 视觉方向 | 05-style-tiles ×3 | **挑方向** | 品味类 | ✗ | L1+L2 |
| 6 | 设计系统 | 06-tokens.json+样张 | 确认 | 事实类 | ✓ | L1+L2 |
| 7 | 高保真 | 07-hifi（关键屏先行→铺全量） | 对齐→放行铺开 | 事实类 | ✓ | L1+L2 |
| 8 | 交互+crit | 08 三件 | 审 crit 处置 | 豁免类 | ✗ | L1+L2 |
| 9 | 规格导出 | 09-spec.md | — | 事实类 | ✓ | L1+L2 |

每阶段执行前**加载对应 `references/stage-0N-*.md` 任务卡**（含产物模板、完成标志、网页工具映射）；
L2 评审前**加载对应 `references/rubric-0N.md` 判据卡 + `references/review-conventions.md` 评审公约**（判据离散三值判定，findings 契约与放行语义见公约）。

<HARD-GATE>
1. **阶段推进按模式确认**：step=每阶段人工确认后推进；auto=事实类阶段（2/3/6/7/9）双层 gate 放行即推进，答案类（1）/品味类（4/5）/豁免类（8）仍必停人工。所有拍板（人工或 auto 代批）必须当日追加进 `01` 决策台账，auto 代批标注来源。
2. **HTML 产物必须过 `scripts/check_artifacts.py`**：标签配平 + 固定画布 + 负面文案，三查全绿才算完成（ERROR 无豁免）。
3. **crit 🔴 清零才定稿**：十维度每维必有结论，🔴 必修，🟡 必处置（修复/豁免记录），未决挂 U-x 回需求层。
4. **结构改动回阶段 4 备案**：高保真阶段发现结构问题，记 P4-x 进台账后修线框与高保真，不允许只改高保真。
5. **auto 放行条件（三合一，缺一不可）**：L1 脚本 gate 全绿 AND L2 评审 🔴=0 且判据覆盖完整 AND 累计重试 ≤2（生成打回与评审打回共享预算）。重试用尽转人工，失败无损；🟡 可带病通过但必须记录在案。
6. **评审独立性**：L2 评审只读产物、只出 findings（🔴/🟡+证据）、禁止打分、禁止改产物；verdict 由编排引擎数出，不归评审器裁量。
</HARD-GATE>

## 网页工具映射（本 skill 即工具内核的规格）

本 skill 的每张阶段任务卡是未来网页工具的编排单元：

- **阶段卡 = 一次有界 AI 调用**（headless 会话，读工作区产物，写本阶段产物，不带跨阶段会话记忆）；
- **人工决策点 = 界面确认控件**（问题单表单/变体并排挑选/crit 处置审批）；auto 模式下事实类决策点由引擎代批（source=ai_review），品味/答案/豁免类仍走控件；
- **gate = 双层**：L1 后端脚本（确定性）+ L2 评审调用（独立 headless 会话，输入=判据卡+产物，输出=findings JSON）；通过条件 = L1 绿 AND 🔴=0（生成成功 ≠ 任务成功，过双层 gate 才算）；
- **重试预算共享**：L1 打回与 L2 打回合计 ≤2 次，超限转人工（防生成器讨好评审器）；
- **决策台账 = 数据库记录**（可审计、可回放，含人工/auto 来源）；
- **产物 = 文件工作区**（版本 = 快照）。

各阶段卡内"工具化要点"一节是该阶段接入网页工具的具体契约。

## 反模式

| 反模式 | 正确做法 |
|---|---|
| 一次生成全部页面 | 九阶段逐步，关键屏先行 |
| 用分数阈值放行（"≥8 分过"） | 离散 findings：🔴=0 才过，分数是弱信号且可被磨软 |
| 生成器自评/评审器顺手修产物 | 评审只读只出 findings；修复独立定点做 |
| 无限重试讨好 gate | 重试预算共享 ≤2，超限转人工 |
| 中间产物当交付物精雕 | 消耗品：画错就扔，只有 06/07/09 是契约 |
| 整批页面一起生成保一致 | token/组件/画布规则一次定义，逐屏组装 |
| HTML 画布自适应尺寸 | 锁定当前项目画布（独立使用未提供时默认手机 390×844），放不下=改布局（密度问题灰框期就该现形） |
| lorem/占位文案 | 真实感样例数据从低保真起就有 |
| 浮层绝对偏移定位 | 居中覆盖层（遮罩+降饱和） |
| 审计时顺手修 | crit 只出 findings，修复独立定点做 |
| 高保真直接改结构 | 回阶段 4 备案 P4-x，线框高保真同步 |
| 每屏自由发明布局 | 布局模式从枚举选，理由记台账 |
| 视觉问题靠像素微调 | 改 token/组件，重出屏 |

## 参考资源

- **`references/stage-01-understanding.md` … `stage-09-spec.md`** —— 九张阶段任务卡。**逐阶段加载**（生成侧）。
- **`references/rubric-01.md` … `rubric-09.md`** —— 九张评审判据卡。**L2 评审前加载**（评审侧，与生成任务卡分离加载）。
- **`references/review-conventions.md`** —— 评审公约：findings JSON 契约、独立性硬约束、放行语义、决策类别、校准方法。
- **`references/html-conventions.md`** —— 画布/浮层/wireframe token/负面清单等 HTML 公约。**阶段 4/5/6/7 生成 HTML 前必读**。
- **`scripts/check_artifacts.py`** —— L1 三合一 gate。**阶段 4/7 完成前必须运行**。画布按项目目标参数化（`--canvas-width/--canvas-height`，默认 390×844=手机）；回归测试 `scripts/test_check_artifacts.py`。
- **参照示例 / 金标准语料（可选，本地自备）**：任何完整走通本流程的历史项目全套产物（九阶段齐、决策台账、三 gate 全绿的状态帧、crit 记录、09-spec）都可作参照——模板与金标准的差异=本 skill 的通用化改动；也可作**评审器校准集**（金标准跑 L2 评审 🔴 必须为 0；工具经 `--gold` / `WB_GOLD_DIR` 指定目录）。本 skill 自包含，不依赖任何外部固定路径。

## 边界

- **不做**：工程代码导出、真实后端、多人协作、画布式手动编辑器、原生 App 渲染。
- **规模**：单工作区 ≤12 屏；超限先拆工作区。
- **修改词汇四层级**：内容（文案/数据）/组件（换件改配）/布局（回阶段 4）/风格（改 token 重出）。
- 需求文档的质量前提：有用户/场景/规则描述；纯一句话想法先走澄清流程再进本 skill。
