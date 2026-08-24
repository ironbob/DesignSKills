# 阶段 8：交互说明 + 可点原型 + Crit（任务卡）

三件事：把状态语义定成**矩阵契约**、把主流程做成**可点原型**、对全量屏做**独立 crit**。阶段 7 交付的是单屏状态帧；本阶段把它们整合成**唯一的 `08-prototype.html`**——手机（mobile_app）项目即原型工作台，不再平铺静态页。

## 产出

**1. `08-交互说明.md`：**

- **核心屏模式×状态矩阵**：行（进入准备/进行/异常中断含阈值变体/结束/正交标志）×列（模式），每格有值或"—（不适用）+原因"；
- **转场标注表**：迁移 / 转场方式 / 时长缓动（进沉浸屏=底部上推；屏内状态=交叉淡入；反馈类=快 80ms；拍点同步类=120ms linear）；
- **未决 U-x**：需求层歧义记录倾向方案，编码按倾向实现留切换。

**2. `08-prototype.html`（唯一最终原型，按项目目标端二选一）：**

- **手机（mobile_app）→ 原型工作台**（不再是静态帧平铺）：
  - 左 `.workbench-sidebar`（≈280px）：项目名、版本/日期、流程摘要；按模块分组页面列表（编号、页面名、简短状态），当前页高亮；点击任意页面项手机立即切到对应页面/状态；
  - 右主舞台：居中完整手机机身；内部 `.device-frame` 严格=项目画布宽高（锁宽锁高、内部滚动、禁止溢出拉伸）；手机下方 `.device-caption` 显示当前页面说明、当前状态、可执行交互提示；「重置流程」等调试控制可选，放外壳，不得替代手机内真实控件；
  - **interaction manifest**：`<script type="application/json" id="interaction-manifest">` 内嵌 JSON（screens：id/name/module/states；routes：from/to 均为 `screenId@stateId`、control、label、event∈tap/input/select/submit/back/reset、feedback、tags）；页面列表、手机内交互、说明面板**共享同一状态机/路由表**渲染——禁止静态平铺、禁止点击后无变化；
  - **主流程每一步由手机内真实控件触发**；侧栏只是测试与浏览入口，不冒充产品交互、不污染手机内部产品页面；
  - 覆盖五类路径（routes tags 至少各一条）：`main` 核心任务 / `success` 成功出口 / `cancel` 取消返回 / `error` 异常或校验失败 / `recover` 恢复重试；manifest 无悬空目标、起点到成功出口可达、手机内 `<section data-screen data-state>` 与 manifest 双向一致（L1 gate 机械校验）；
  - 双击可开、无网络无框架依赖：内联 CSS/JS，禁止外部资源引用；输入、Tab、筛选、保存、弹层确认等控件必须改变可见状态（仅视觉按钮无行为=断链）。
- **桌面/Web（desktop_app、web）→ 单文件可点原型**：`.frame` 锁项目画布 + 右上角流程定位条（随时显示走到哪步），覆盖起点屏→…→核心屏全部状态→出口。

**3. `08-findings.md` + `.stage8-findings.json`**（crit，十维度逐屏过）：

| # | 维度 | 级别 |
|---|---|---|
| 1 单一焦点 / 2 层级清晰 / 3 模式兑现 / 4 文案纪律 | 🔴 |
| 5 密度留白 / 6 对齐 / 7 跨页一致 / 8 状态完备 / 9 视口 | 🟡 |
| 10 微文案 | 🟢 |

finding 格式：`[Fx]（维度）位置（文件+区块）＋证据＋处置`。**每维度必有结论**（finding/过/不适用），沉默即违规。🔴 必修且修复后复审；🟡 处置=修复/豁免记录/进规格。

`.stage8-findings.json`（决策数据，界面审批消费）：

```json
{
  "dims": [{"dim": 1, "name": "单一焦点", "verdict": "pass|finding|na"}],
  "findings": [
    {"id": "F1", "dim": 5, "severity": "red", "location": "S2.html 底部", "evidence": "…",
     "proposed": "fix", "fix_record": "已改 X · 复审通过"},
    {"id": "F2", "dim": 6, "severity": "yellow", "location": "…", "evidence": "…", "proposed": "spec|fix|exempt"}
  ],
  "u_items": [{"id": "U-1", "text": "…", "proposal": "倾向方案"}]
}
```

## 完成标志（L1 gate）

十维结论齐（1–10 每维有 verdict）；🔴 全部带 fix_record（清零）；🟡 全部有处置建议；U-x 全部有倾向；矩阵/转场表存在；原型过 HTML gate 四查（TAG/CANVAS/COPY/PROTOTYPE——手机项目含工作台结构、manifest 无悬空、五类覆盖、起点→出口可达、section 同步、无外部资源；桌面/Web 含流程定位条）。静态查不了的点击行为由工具后端浏览器验证兜底（manifest 即点击测试脚本）。

## 工具化要点

- 决策类型=crit：界面按 `.stage8-findings.json` 出审批清单（🟡 三选一处置 + U-x 倾向确认）；**豁免处置须显式人工确认**（confirm_exemptions）。豁免类：任何模式必停人工。
- crit 独立性：工具里每次 AI 调用本无记忆，天然 fresh context。
