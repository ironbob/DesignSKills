# HTML 公约（阶段 4/5/6/7/8 生成 HTML 前必读）

> 全部来自实战踩坑，配套 `scripts/check_artifacts.py` 四查 gate 机械执行。

## 1. 固定画布（防"屏幕不固定手机高度、组件挤在一起"）

画布 = **当前项目的目标画布**（网页工具按锁端预设给定：手机 390×844 / 桌面 1280×800 / Web 1440×900）；独立使用本 skill 且未提供画布时，默认手机 **390×844**。默认值不是唯一合法尺寸——生成与 gate 都跟随项目画布参数：

```css
.frame{
  width:390px; height:844px;      /* =项目画布（示例为默认手机）；锁宽锁高，box-sizing:border-box */
  display:flex; flex-direction:column; overflow:hidden; position:relative;
}
```

- 长内容（谱面/列表/编辑器）= `flex:1; overflow:hidden; min-height:0` 的**内容区内部滚动**，禁止整屏长高；
- 页面多帧并排演示：`body{display:flex;flex-wrap:wrap;gap:40px}`，每帧上方一行灰字帧标签（`① 状态名`）、下方标注（设计理由）。
- **放不下 = 改布局（减键/合并/分层），不是撑高度。**

## 2. 浮层（防绝对偏移错位）

```css
.overlay{position:absolute; inset:0; background:rgba(0,0,0,.28); display:flex;
         align-items:center; justify-content:center; padding:24px}
.overlay .sheet{…}                 /* 内容自适应，居中呈现 */
.veiled .score,.veiled .ctrl{filter:saturate(.5) brightness(.96)}  /* 底衬降饱和不消失 */
```

## 3. wireframe token（阶段 4 专用灰阶）

| 槽 | 值 |
|---|---|
| bg / ink / ink_weak | #ffffff / #333333 / #888888 |
| surface / surface_alt / line | #f2f2f2 / #e6e6e6 / #cccccc |
| accent | #555555 |
| radius | 4px；间距/字号刻度 8/16/24/32/48 与 12/14/16/20/28 |

规则：无色彩无阴影无图片（媒体类画对角线灰框+说明文字）；**图标以文字代替**；字号字重差是唯一层级手段；**真实内容标签，禁止 lorem——灰块也要是真数据**；触控目标画足 ≥48px 高。

## 4. 文案纪律（负面清单，gate 扫描 HTML 全文本）

命中任何一条 = ERROR，无豁免（这些词出现=模型在用加法对冲不确定性）：

`欢迎` `欢迎使用` `本页面` `本页用于` `该页面` `示例文本` `示例：` `占位` `待补充` `待填写` `lorem` `ipsum` `TODO` `FIXME` `点击这里` `此处显示` `xxx` `XXX` `???` `测试数据` `假数据` `这是` `以上是`

清单与 `scripts/check_artifacts.py` 的 `BANNED_COPY` **逐词一一对应**——改任何一侧必须同步另一处（`scripts/test_check_artifacts.py` 有配平断言，漂移即测试红）。

正面要求：展示值=真实感样例数据（人名/公司/金额/日期/业务语感中文）；按钮=动词+宾语；列表 3–8 条样例；空态=为什么空+下一步。

## 5. 标签配平（防 `</span>` 误写 `</div>` 破整屏版）

写完自查 div/span 开闭计数；提交前跑 gate。**手工 HTML 的固有税，gate 兜底。**

## 6. 单文件自包含

内联 CSS/JS，无外部依赖，双击可开；**禁止引用任何外部 http(s) 资源**（`src`/`href`/`@import`/`url()` 都不许指向网络——gate DEPS 查机械拦截）；可点原型用极简 JS 状态机（`go(viewId)` 切 view + 流程定位条；mobile 工作台用 `go(screenId, stateId)` 走共享路由表，见 §8）。

## 7. gate 命令

```bash
python skills/ui-prototype-gen/scripts/check_artifacts.py <目录或文件>… \
  [--canvas-width 390] [--canvas-height 844] [--platform mobile|desktop|web]
# 画布参数=当前项目目标画布（如 Web 1440×900 两参都传）；默认 390/844=手机。
# --platform 跟随 tokens 目标端（默认 mobile）：mobile 时 08-prototype.html 必须是 §8 工作台。
# index/对照板无 .frame 自动跳过画布检查。回归：python scripts/test_check_artifacts.py
```

四查：TAG（div/span 配平）→ CANVAS（含 .frame 规则的文件必须锁宽锁高；工作台文件验 `.device-frame`）→ COPY（负面清单）→ PROTOTYPE（工作台结构 + manifest + 同步 + DEPS 无外部依赖，仅对声明工作台/mobile 原型生效）。任一 ERROR 退出码 1，无 HTML 可查退出码 2。

rapid 设计模式**不改变本公约任何一条**（画布/单文件/内部滚动/浮层/负面清单/工作台契约照旧）——模式只减候选数与确认数，不减 HTML 规则。

## 8. 原型工作台（阶段 8 mobile 交付形态）

当 `06-tokens.json` 目标端为 mobile 时，`08-prototype.html` **不是静态帧平铺**，而是桌面原型工作台：左侧页面列表 + 右侧手机舞台。两层职责不同，类名即契约（gate 按类名机械校验）：

| 层 | 类名/标记 | 规则 |
|---|---|---|
| 工作台外壳 | `.prototype-workbench` | 桌面浏览器响应式铺满；**不受**手机固定画布约束（gate 不会把外壳当手机画布查） |
| 页面列表 | `.workbench-sidebar`（≈280px） | 项目名、版本/日期、流程摘要；按模块分组页面列表（编号、页面名、简短状态）；当前页高亮；点击任意页面项手机立即切到对应页面/状态——只是**测试与浏览入口**，不替代手机内真实控件 |
| 手机画布 | `.device-frame` | **唯一产品画布**：锁定 tokens.canvas 宽高（如 390×844）、内容内部滚动、禁止溢出拉伸；gate 对 `.device-frame` 施加与 `.frame` 相同的锁宽锁高校验 |
| 舞台说明 | `.device-caption` | 手机下方：当前页面说明、当前状态、可执行交互提示；调试控制（重置流程/上一步/下一步）可选放此处，不得替代手机内真实控件 |

**interaction manifest（可审查路由表）**：`<script type="application/json" id="interaction-manifest">` 内嵌 JSON：

```json
{"meta":{"project":"…","version":"…","date":"…","entry":"library@default"},
 "screens":[{"id":"library","name":"乐谱库","module":"乐谱","states":["default"]}],
 "routes":[{"id":"r01","from":"library@default","control":"[data-action=open-detail]",
            "label":"曲目行《良宵》","event":"tap","to":"detail@default",
            "feedback":"进入乐谱详情","tags":["main"]}]}
```

交互契约（gate 静态校验，缺一即 ERROR）：

1. **manifest 必须声明**且 JSON 可解析；`from`/`to` 均为 `screenId@stateId`；`event` ∈ tap/input/select/submit/back/reset；
2. **无悬空目标**：每条路由 from/to 都在 screens 声明中；从 `meta.entry` 出发经**手机内路由**可达 success 出口；全部屏×状态可达（路由可达 ∪ 侧栏 `data-goto` 浏览可达）；
3. **五类覆盖**：routes 的 tags 至少各出现一次 `main`（核心任务）/`success`（成功出口）/`cancel`（取消返回）/`error`（异常或校验失败）/`recover`（恢复重试）；
4. **HTML ↔ manifest 同步**：手机内每屏用 `<section data-screen="…" data-state="…">` 呈现，屏×状态集合与 manifest 双向一致；侧栏页面项 `data-goto` 指向 manifest 中存在的屏或屏状态，且每个屏至少一个入口项；
5. **共享状态机**：侧栏切页、手机内控件、说明面板由同一状态机/路由表渲染（说明面板的可执行交互直接从 manifest 当前节点推导），禁止静态平铺、禁止点击后无变化；
6. **控件必有可见状态反馈**：输入、Tab、筛选、保存、弹层确认等改变可见状态；仅视觉按钮而无行为=断链（crit R8-4 命中）。

桌面 Web / 桌面软件项目**不启用**工作台：`08-prototype.html` 按 §1 固定目标画布做单文件可点原型（`.frame` + 流程定位条）。
