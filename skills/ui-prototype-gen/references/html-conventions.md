# HTML 公约（阶段 4/5/6/7 生成 HTML 前必读）

> 全部来自实战踩坑，配套 `scripts/check_artifacts.py` 三 gate 机械执行。

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

内联 CSS/JS，无外部依赖，双击可开；可点原型用极简 JS 状态机（`go(viewId)` 切 view + 流程定位条）。

## 7. gate 命令

```bash
python skills/ui-prototype-gen/scripts/check_artifacts.py <目录或文件>… \
  [--canvas-width 390] [--canvas-height 844]
# 画布参数=当前项目目标画布（如 Web 1440×900 两参都传）；默认 390/844=手机。
# index/对照板无 .frame 自动跳过画布检查。回归：python scripts/test_check_artifacts.py
```

三查：TAG（div/span 配平）→ CANVAS（含 .frame 规则的文件必须锁宽锁高）→ COPY（负面清单）。任一 ERROR 退出码 1，无 HTML 可查退出码 2。

rapid 设计模式**不改变本公约任何一条**（画布/单文件/内部滚动/浮层/负面清单照旧）——模式只减候选数与确认数，不减 HTML 规则。
