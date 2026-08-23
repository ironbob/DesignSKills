# doc-renderer · VitePress 渲染底座（spike）

expert-doc-writer 的渲染层验证：把 Q3 述职报告（`docs/2026-08-23-q3-ops-report/08-doc.html` 手写版）重做到 VitePress + 组件库，验证「图表/流程图/表格的稳定输出」。

## 运行

```bash
cd doc-renderer
npm run dev       # 开发预览 http://localhost:5173
npm run build     # 产物 dist/（静态站）
npm run preview   # 预览构建产物 http://localhost:4173
```

## 架构（稳定性的来源）

```
.vitepress/
  config.mts              # withMermaid(vitepress) —— mermaid 主题与文档品牌色同源
  theme/
    style.css             # 设计 token → VitePress 主题变量（一处改动，全文生效）
    chartTheme.ts         # ★ 统一图表主题层：withTheme() 注入字号/配色/网格/标注规范
    app.ts                # 全局组件注册
    components/
      FigureChart.vue     # ECharts 封装：option 纯数据进、观感统一出；Resize 自适应；降级=slot 文本
      KpiRow.vue          # KPI 大数字行（网格对齐由构造保证）
      Callout.vue         # conclusion / risk / data 三型
      CompareMatrix.vue   # 对比矩阵（pick 行高亮）
  data/charts.ts          # 图表数据层：数字与 02-事实台账同源
index.md                  # 内容页 = markdown + 组件数据装配（不再是手写 HTML）
```

## spike 验证记录（2026-08-23）

- 构建：一次通过（6s）；chunk 体积警告（echarts/mermaid 全量引入）可后续按需 tree-shake
- DOM 实测：ECharts SVG ×3、Mermaid SVG ×2、KPI 卡 ×7、callout ×5、矩阵行 ×4、降级文本 0 外露、七节 h2 齐
- 独立视觉评审（AI vision，1-10 分）：图表一致性 8 / 排版专业度 7 / 设计感 8 / 密度对齐 7；指出的缺陷（间距/辅助色）全部落在 style.css / chartTheme.ts 单点可调——对比手写版「每篇每图各调」是本质差异
- **D-012 修复（同日）**：FigureChart 降级文本残留 flex 容器导致图表右移溢出（屏幕+PDF 均丢右侧柱系）；修复后像素断言全绿。`docs/public/print-test.html`（+本地 echarts.min.js）留作打印/布局回归探针。

## 交付形态（不依赖常驻服务器）

| 形态 | 命令/方式 | 适用 |
|---|---|---|
| PDF（推荐） | Playwright `page.pdf()` 或浏览器 Cmd+P（开背景图形） | 述职投屏/传阅/存档，零运行时依赖 |
| 静态站 | `npm run build` → dist/ 挂任意静态托管 | 多文档门户、可搜索 |
| 本地浏览 | `npm run preview`（或 `python3 -m http.server -d .vitepress/dist`） | 写作期审阅 |

注意：dist 产物**不能 file:// 双击直开**（ES 模块被 CORS 拦）；单文件内联方案已试（vite-plugin-singlefile）不可行——VitePress 多入口与 rollup `inlineDynamicImports` 冲突，详见工作区 deviations D-011。

## 与手写版（08-doc.html）的对照结论

| 痛点 | 手写 HTML | VitePress 底座 |
|---|---|---|
| 图表观感 | 每图手配 option，观感漂移 | chartTheme.withTheme 统一注入 |
| 排版专业度 | 手写 CSS | VitePress 排版引擎 + token 变量 |
| 设计感 | 靠单篇手艺 | 主题一次定制，篇篇一致 |
| 密度对齐 | 手工 margin | 组件网格构造性对齐 |
| 交付 | 单文件（离线可开） | 静态站链接 + 打印 PDF（多页导航/搜索附赠） |

## 待定（若采纳为 skill 渲染层）

- skill 阶段 5/6/7/8 的任务卡改写：视觉方向=主题档位、排版系统=主题+组件、分节成稿=md+组件数据、check_doc 改跑源文件或 dist
- 单文件离线场景（无网投屏）是否保留手写档作为降级输出
