# AI 设计工作台（app/）

把九阶段专家设计工作流（`skills/ui-prototype-gen/`）产品化为本地网页工具：**它生成，你拍板，gate 守质量**。
产品契约：`prototype_ux_ui_design_web_system/design/09-spec.md`（桌面浏览器专用，1440×900）。

## 运行（一键）

```bash
bash start.sh        # 仓库根执行：自检依赖→自动安装→起双服务→自动开浏览器（:5180）
AI_RUNNER=claude bash start.sh   # 真实 claude CLI 生成（消耗配额）
```
等价入口：`make dev`（app/ 内）或 `app/dev.sh`。

- **AI_RUNNER**：`mock`（默认，罐头产物，不烧配额）/ `claude`（真实 CLI 子进程）
- **AI_REVIEWER**：L2 评审器，默认跟随 runner（mock 配 mock / claude 配 claude）；可单独覆盖为 `off`（只跑 L1）
- **WB_DATA_DIR**：数据目录（默认 `<repo>/.workbench-data`——磁盘是唯一真相源）
- 测试：`make test`（58 项，mock 模式）；真实冒烟：`make smoke`（阶段 1 全链路，约 1-2 分钟，消耗配额）；判据卡校准回测：`make calibrate GOLD=<本地金标准目录>`（或 `WB_GOLD_DIR`；跑 L2 评审，🔴 必须为 0——语料自备，仓库不内置路径）

## 实现范围与验证状态（非完整产品，如实区分）

**完整九阶段目标** = 九个阶段都能用真实 claude runner 走通、判据卡经金标准校准回测。**当前尚未达到**，差距如下：

| 范围 | 状态 |
|---|---|
| 引擎/双层 gate/auto 模式/四类决策/台账快照 | ✅ 已实现，mock E2E 全绿 |
| 阶段 1-9 任务卡、L1 gate、mock 产物 | ✅ 已实现（卡快照+罐头在 `stages/cards/`） |
| 三端画布 390×844 / 1280×800 / 1440×900 | ✅ 生成（prompt 画布硬约束+mock 罐头按项目画布改写）· 验证（gate 必传项目画布，缺画布=失败不回退默认）· 预览（iframe 按项目画布 1:1/适应）；仅未指定端才默认手机 |
| rapid 设计模式（与 run_mode 正交） | ✅ mock E2E 全绿：阶段 1 仅阻塞问题打断（非阻塞默认入台账 source=rapid_default）；4/5 单候选（引擎代记台账+理由）；8 无豁免自动处置；阶段 9 后一次最终验收（awaiting_acceptance→done，展示规格/默认决策/U-x/🟡/契约文件）；L1/L2/重试/🔴 阻断全部不变；模式由引擎注入生成与评审 prompt（评审器不自选，判据卡候选数条目按 not_applicable 处理）；deliberate 行为与判据完全不变（回归测试锁定）；既有项目经迁移默认 deliberate |
| 阶段 1 真实 claude runner | ✅ M1 时期冒烟通过；M1.5/M2 引擎改动后未重跑 |
| 阶段 2-9 真实 claude runner | ⏳ **未运行**（当前仅 mock 验证） |
| 判据卡校准回测（calibrate） | ⏳ 未运行（语料自备，见上） |
| 独立画廊/审批页（S5b/S5c）、修改流、历史视图、导出文件包 | ⏳ M2 路线（gallery/crit 现为决策弹窗内联实现） |

## 已实现（引擎与界面）

- **对象两级**：产品（共享需求文档）→ 项目（锁端即锁画布：手机App 390×844 / 桌面App 1280×800 / Web 1440×900，三端平级无手机偏好）。两个**正交**模式字段：**run_mode**（step=每阶段人审 / auto=事实类过双层 gate 自动推进）决定推进方式；**design_mode**（deliberate 默认=多候选探索 / rapid=快速实现）决定候选数量、默认决策与打断密度——rapid+step、rapid+auto 均合法
- **四屏**：S1 产品列表（卡片墙+空态）/ S2 新建向导（两步·锁端+模式选择）/ S3 工作台（阶段轨 208 + 预览台 iframe + 右栏 336：任务卡·决策卡·失败卡）/ 决策弹窗四态（问题单逐题·确认·画廊挑选（变体并排+混搭）· crit 审批（🟡 处置+U-x 倾向+豁免显式确认））
- **任务引擎**：全局串行队列（R7）· 态机 `queued→running→gate_running→review_running→(共享重试 ≤2，总执行 ≤3)→failed_needs_human|awaiting_decision→completed` · SSE 事件流（步骤/产物增量/gate 结果/**评审 findings**，回放 200 条）；gate 自身异常按打回处理（不挂死）
- **双层 gate（L1+L2）**：L1 脚本 gate（结构校验）+ L2 独立 AI 评审（判据卡 rubric-01..09，只出 findings 🔴/🟡+证据，verdict 由引擎数出 🔴=0；判据覆盖不完整=评审不可信等同打回；评审打回与生成打回共享重试预算）
- **auto 模式代批**：事实类阶段（2/3/6/7/9）过双层 gate 即记台账（source=auto）自动进下一阶段；答案类（1）/品味类（4/5）/豁免类（8）必停人工
- **阶段卡注册表（九阶段全量注册，卡快照+mock 产物在 `stages/cards/`）**：1 需求消化（问题单 JSON+结构 gate）· 2 流程草图（mermaid 无断链/无孤儿）· 3 屏幕与IA（闭环检查/关键屏提名/孤儿屏/≤12 屏）· 4 关键屏灰框（gallery：v1/v2 齐+对照板决策问题+HTML 三查+异常态帧）· 5 视觉方向（gallery：三 tile+对照表）· 6 设计系统（tokens schema/语义三元组/规则十二条/canvas=项目画布+样张）· 7 高保真（盘点屏全覆盖+状态帧+HTML 三查）· 8 交互与crit（crit：十维结论/🔴 清零带修复记录/🟡 处置建议/U-x 倾向+矩阵转场+原型定位条+`.stage8-findings.json`）· 9 规格导出（十节结构/契约三件套存在/参照帧存在性）。HTML 三查 gate 用工具内快照 `stages/check_artifacts.py`（与 skill 侧逐字节同步，测试锁定）
- **决策闭环（四类决策全量）**：question_form（逐题拍板）/ confirm（3/6/7/9 走向确认）/ gallery（4 变体可混搭、5 方向挑选，选项从产物文件派生）/ crit（8 处置审批：🟡 三选一+U-x 倾向，**豁免须显式确认**）→台账（decisions 表）→快照（snapshots/#N）→解锁（R1/R3/R6）；每次 L2 评审落 reviews 表；`/ledger` 返回 decisions+snapshots+reviews（可审计可回放）
- **ClaudeRunner / ClaudeReviewer**：`claude -p --output-format stream-json` 子进程，prompt 走 stdin（每阶段 prompt 内嵌**项目画布硬约束**：.frame 必须 width:{W}px; height:{H}px），产物增量从 tool_use 解析，超时进程组杀；评审会话 fresh context 只读产物（防错误相关）
- **跨平台画布**：mock 罐头按手机预制，复制到项目时自动改写为项目画布（.frame 宽高 / tokens.canvas / 文案字样）；`test_canvas_platforms.py` 锁定三端 gate 通过与宽高不一致必失败、缺画布必失败

## M2 路线（达成"完整九阶段目标"的差距）

1. 真实 claude runner 重跑阶段 1 冒烟并跑通阶段 2-9（当前仅 mock）；随后 `make calibrate GOLD=…` 判据卡回测
2. 独立画廊/审批页（S5b/S5c，现为决策弹窗内联）、S7 修改流、S8 历史视图、S9 导出浮层（契约三件套打包下载）

## 布局

```
app/
  backend/   FastAPI（engine/ 任务引擎+runner+事件 · stages/ 卡注册表 · routers/ · tests/）
  frontend/  Vue3+Vite+TS+Pinia（pages/ 两视图 · components/ 手写组件族 · tokens.css=工房变量）
  dev.sh · Makefile
```
