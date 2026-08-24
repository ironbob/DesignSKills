# 阶段 7：分节成稿（任务卡）

## 目的

按 `04` 形式清单逐节成稿——产物是 **markdown + 组件数据**，不是 HTML：每节一个 `sections/sN.md`，图表数字集中在数据层与事实台账同源。**关键节先行**（03 的 ★节先写**先自检**——过 `check_doc --md` + build/preview 渲染检查——通过后**直接铺全量**，无人工放行）。

## 输入

`03`（message 与节奏）+ `04`（形式与标题草案）+ `06`（底座组件/档位）+ `02`（图表数据与口径）。

## 产出（渲染内容目录 `doc-renderer/docs/<slug>/`）

```
docs/<slug>/
  index.md                  # 骨架：doc-head + charts 数据 import + @include 各节
  sections/s1.md … sN.md    # 分节片段（底座 srcExclude 排除，不生成独立页面）
```

- 图表数据层：`.vitepress/data/<slug>.charts.ts`（或就近 data 模块）——每张图的 option 只写**数据+意图**（类目、系列、标注文案），颜色/字号/网格由 `withTheme()` 统一注入；
- 每节内部结构固定：

```markdown
## 节名（=message 短语版） {#sN}
<p class="lead">message 原句</p>
（正文短段；按 04 该节清单装配组件）
```

成稿纪律：

1. **每节 message 双重显形**（h2 + `.lead`），扫标题链能复述论点；
2. 图表数据照抄台账（单位/基数按 02 数字规范），option 数字与 `charts.ts` 一致；
3. 段落纪律：单段 ≤180 字（WALL 红线），流程叙述=Mermaid 围栏，数字罗列=图/表；
4. 论证块 = 短段落 + `<Callout>`，不图化；
5. `<FigureChart>` 三件套必填：`caption`（结论式）/`source`（来源口径）/`fallback`（降级文本）。

## 完成标志

`check_doc.py docs/<slug>/ --md` 全绿；每节有显形 message；04 清单每个视觉件落地且 caption 与草案一致（改标题=改 04 备案）。

## 默认决策策略（关键节自检）

**★节自检通过即铺全量**：★节先写，跑 `python3 skills/expert-doc-writer/scripts/check_doc.py doc-renderer/docs/<slug>/ --md` + `cd doc-renderer && npm run build && npm run preview` 实渲染检查（**dev 模式有 fastdom ESM 已知问题，不用于验证**）；渲染异常（图空白 / 降级文本外露 / 溢出）修复后才铺全量——纠错窗口保留，人工等待删除。

## 坑

- 一次写完全部才自检——关键节先行的纠错窗口被浪费；
- 图表数据入稿时口径漂移（台账 5.3min 入稿变 5 分钟）；
- 超出 04 清单自行加图/删图（加减必须回 04）；
- **内部台账编号（F-x/D-x）漏进受众正文**——证据写事实锚点本身，编号只留过程文件；
- option 里写颜色/字号裸值绕过 chartTheme（观感漂移）。

## 工具化要点

- AI 任务：每节一次有界调用（输入=03 行+04 行+02 数据行，输出=单节 md + charts 数据段）。
- 界面：节卡片流 + 实渲染预览 + 数据回链。
- gate：`python3 skills/expert-doc-writer/scripts/check_doc.py doc-renderer/docs/<slug>/ --md`（WALL/CHART/FIG/SRC/NAV/COPY）。
