# 渲染底座公约（doc-conventions）

阶段 5/6/7/8 使用。载体 = **doc-renderer 底座**（VitePress + 组件库 + 统一图表主题层），不是手写 HTML。

## 底座结构（`doc-renderer/`）

```
.vitepress/
  config.mts             # withMermaid；srcDir=docs；srcExclude=['**/sections/**']；nav 按文档登记
  theme/
    style.css            # 设计 token → VitePress 主题变量（--doc-* / --vp-c-brand-*）
    chartTheme.ts        # ★统一图表主题层：withTheme() 注入字号/配色/网格/标注
    app.ts               # 全局组件注册
    components/          # KpiRow / FigureChart / Callout / CompareMatrix（+定向扩展）
    presets/             # 主题档位（阶段 5 产出/选择）
  data/<slug>.charts.ts  # 每篇文档的图表数据层
docs/<slug>/
  index.md               # frontmatter + doc-head + 数据 import + @include 各节
  sections/s1.md … sN.md # 分节片段（srcExclude 排除，不成独立页面）：
                         #   h2{#锚点} + p.lead + 正文 + 组件 + mermaid 围栏
```

规划产物（00–04、findings、deviations）仍在 `<workspace>/`（`docs/<日期>-<slug>/`），与渲染内容目录分工：**workspace=过程，doc-renderer/docs=内容**。

## 组件用法（源 md 里的固定形态）

```markdown
## 节名（message 短语版） {#sN}
<p class="lead">message 原句</p>

<KpiRow :items="[{ num: '12.8', unit: '万', label: '新增注册用户', delta: '环比 +23%', deltaType: 'up' }]" />

<FigureChart
  :option="chartVar"            ← index.md 的 script setup 里 import 自数据层
  caption="结论式标题（断言）"
  source="来源 + 口径 + 置信档"
  fallback="降级文本：图没了也能读懂的结论句" />

<Callout type="conclusion|risk|data">断言/风险/口径</Callout>

<CompareMatrix :columns="[...]" :rows="[{ cells: [...], pick: true }]" />
```

## 图表纪律（观感稳定的核心）

- option **只写数据与意图**（类目/系列/标注文案/排序），颜色/字号/网格一律由 `withTheme()` 注入——option 出现颜色/字号裸值 = 违例（crit ⑥ 查）；
- 常用图型用数据层构造器（`pairBars` 等），新图型先加构造器再用；
- 数据层数字与 `02-事实台账` 逐位同源，换算进标题须注明；
- `fallback` 必填：无 JS/打印异常时的结论文本（组件内文本即降级，渲染后自然替换）。

## Mermaid

- ```mermaid 围栏直接写（插件渲染，主题变量与文档品牌同源）；
- 结构图规范见 visual-form-catalog T1–T4（节点可带台账数值；对比/趋势数值归 ECharts）。

## 构建、预览与交付

```bash
cd doc-renderer && npm run build     # 静态站 → dist/
npm run preview                      # 预览构建产物
npm run dev                          # 阶段 7 审节用
```

- PDF：浏览器打开页面 → 打印 → 存为 PDF → 开「背景图形」；
- 发布：dist/ 为纯静态，可挂任意静态托管或内网 nginx；wiki 环境按 09 交付说明走投影路线（链接/PDF/图）。

## 文字纪律（WALL 查依据，与手写时代一致）

- 单段 ≤180 字（硬红线 300 字 ERROR）；
- 段内顺序连接词 ≥3 = 流程叙述，转 Mermaid；
- 一段内 ≥3 个独立数值 = 数字段落，转图/表（邻近视觉件=FigureChart/KpiRow/CompareMatrix/表格/mermaid 围栏）；
- 连续 3 段纯论证无视觉件 → 检查形式预算（纯文字节 ≤1/3）。

## 负面清单（COPY 查）

欢迎查阅/本文将介绍/综上所述/示例数据/假数据/待补充/TODO/lorem/xxx/此处省略/见图。
