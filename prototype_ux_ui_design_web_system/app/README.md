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
- 测试：`make test`（34 项，mock 模式）；真实冒烟：`make smoke`（阶段 1 全链路，约 1-2 分钟，消耗配额）；判据卡校准回测：`make calibrate GOLD=<本地金标准目录>`（或 `WB_GOLD_DIR`；跑 L2 评审，🔴 必须为 0——语料自备，仓库不内置路径）

## M1 已实现

- **对象两级**：产品（共享需求文档）→ 项目（锁端：手机App 390×844 / 桌面App 1280×800 / Web 1440×900；**run_mode**：step=每阶段人审 / auto=事实类过双层 gate 自动推进）
- **四屏**：S1 产品列表（卡片墙+空态）/ S2 新建向导（两步·锁端+模式选择）/ S3 工作台（阶段轨 208 + 预览台 iframe + 右栏 336：任务卡·决策卡·失败卡）/ S5a 问题单（卡片逐题·选项三件套·汇总拍板仪式）
- **任务引擎**：全局串行队列（R7）· 态机 `queued→running→gate_running→review_running→(auto_redo ≤1)→failed_needs_human|awaiting_decision→completed` · SSE 事件流（步骤/产物增量/gate 结果/**评审 findings**，回放 200 条）
- **双层 gate（L1+L2）**：L1 脚本 gate（结构校验）+ L2 独立 AI 评审（判据卡 rubric-01..09，只出 findings 🔴/🟡+证据，verdict 由引擎数出 🔴=0；判据覆盖不完整=评审不可信等同打回；评审打回与生成打回共享重试预算）
- **auto 模式代批**：事实类阶段（2/3/6/7/9）过双层 gate 即记台账（source=auto）自动进下一阶段；答案类（1）/品味类（4/5）/豁免类（8）必停人工
- **阶段卡注册表**（stages 3-9 即插即用）：card01 需求消化（产物+问题单 JSON，gate=结构校验+零裸问）· card02 流程草图（mermaid 结构 gate：无断链/无孤儿节点）
- **决策闭环**：提交→台账（decisions 表）→快照（snapshots/#N 目录拷贝）→解锁下一阶段（R1/R3/R6）；每次 L2 评审落 reviews 表（可审计可回放）
- **ClaudeRunner / ClaudeReviewer**：`claude -p --output-format stream-json` 子进程，prompt 走 stdin，产物增量从 tool_use 解析，超时进程组杀（spike 结论：行可 >64KB，32MB 上限+坏行容错）；评审会话 fresh context 只读产物（防错误相关）

## 扩展阶段卡（M2 路线）

1. `backend/stages/cards/stageNN.md` 放卡文本快照（底稿=skill 的 references/stage-NN-*.md，防漂移）
2. `backend/stages/registry.py` 注册：产物路径 / 决策类型（question_form|gallery|crit|confirm）/ gate 实现（HTML 阶段复用 `skills/ui-prototype-gen/scripts/check_artifacts.py --canvas-width <W> --canvas-height <H>`，W/H=端预设）/ mock 罐头放 `cards/mock/stageNN/`
3. 前端按 decision_type 补浮层（画廊=S5b、审批=S5c 已有高保真参照帧）

## 布局

```
app/
  backend/   FastAPI（engine/ 任务引擎+runner+事件 · stages/ 卡注册表 · routers/ · tests/）
  frontend/  Vue3+Vite+TS+Pinia（pages/ 两视图 · components/ 手写组件族 · tokens.css=工房变量）
  dev.sh · Makefile
```
