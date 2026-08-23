# 干跑偏差日志（deviations）——回填 skill 的依据

记录任务卡/脚本与专家实际做法的偏差。格式：D-编号｜阶段｜偏差｜处置（改卡/改脚本/不改并理由）。

- **D-001**｜S1｜check_plan 的「A-x 已答」检查是出现次数启发式（≥2 次），A-x 写进"待答"清单也会误判为已答。｜改脚本：引入显式标记约定（台账条目须含「✅ 已答」才算答）。
- **D-002**｜S1｜论点写在标题行内时，标题残余（如"（候选，待拍板）"）被当作论点内容误报。｜已修：stage1 解析先取行内冒号后的内容，含待/候选标记则回落到扫描后续行。
- **D-003**｜S0｜brief 模板没预设「格式硬约束」输入位（本文种出现"必含四要素+1500字"类客户硬约束，直接影响阶段 3 骨架与阶段 7 字数纪律）。｜改卡：stage-01 的 brief 模板补「硬约束」字段，故事线卡提示先映射硬约束再排节。
- **D-004**｜S2｜置信三档（实测/推算/传闻）没覆盖"用户提供·转述后台"情形——述职类数据几乎全来自口头/文字转述。｜已按「来源列注明转述+建议复核，置信计实测」处理；stage-02 卡的口径说明里把这个约定写成显式规则。
- **D-005**｜S4｜目录缺「指标总览」类型：开局 KPI 大数字行在 T1–T12 无处安放，硬塞 T6 会触发"必须 ECharts"误报。｜已修：目录新增 T13（指标总览→KPI 行，HTML），check_plan VALID_TYPES 扩到 T1–T13。
- **D-006**｜S4｜"Mermaid 只画结构图"红线需要边界细则：社群链路图节点要标台账数值（128 篇/3.2 万人/310 万），这仍是结构图不是数据图。｜已修：目录 T1 规范补一条「节点可带台账数值标注；对比/趋势数值仍属 T6–T9 领地」。
- **D-007**｜S6｜Mermaid 容器降级文本缺显式机制：echarts 的降级文本会被画布自然替换，mermaid 的 `<pre>` 失败时裸奔图语法。gate（SRC 查）正确拦截。｜已修：公约固化「chart-fallback 两态机制」（run() 成功后隐藏，失败保持可见），样张为参照实现。
- **D-008**｜S7｜CHART 查的「邻近视觉件」只认 figure/table，KPI 行/矩阵/时间线等 HTML 视觉组件不算——首屏 lead 段（数字=KPI 卡片预告）被误报 WARN。｜已修：视觉锚集合扩为 figure/table/kpi-row/matrix/timeline，与目录 T5/T12/T13 对齐。
- **D-009**｜底座选型｜手写单文件 HTML（08-doc.html）四项表现效果不稳（图表观感/排版/设计感/密度对齐，用户反馈）；VitePress spike（Q3 报告重做）一次构建通过、DOM 实测全渲染、AI 视觉评审 8/7/8/7。｜已定案：渲染层切换为 doc-renderer 底座（VitePress+组件库+chartTheme），skill 阶段 5-8 任务卡与 check_doc（--md 模式）全部改写；08-doc.html 保留为手写时代金标准参照。
- **D-010**｜底座｜分节 md 放 docs/<slug>/ 顶层会被 VitePress 编译成独立页面（s1.html~s7.html 混入站点）；且 check_doc 目录扫描非递归漏查分节。｜已修：分节统一放 sections/ 子目录 + config srcExclude 排除；check_doc --md 目录改递归扫描（跳过 node_modules）。
- **D-011**｜底座选型｜「离线单文件 HTML」路线实测不可行：vite-plugin-singlefile 依赖 rollup `inlineDynamicImports`，与 VitePress 多入口构建（每页 + 404）直接冲突，rollup 报错拒绝；即便内联，mermaid 动态 chunk 在 file:// 下仍被 ES 模块 CORS 拦。｜定论：无服务器交付走 PDF（Playwright page.pdf / 浏览器打印）；file:// 直开不是本底座支持形态。
- **D-012**｜底座组件｜FigureChart 致命布局 bug：降级文本节点在 echarts init 后残留容器，与图表根 div 并列成 flex 双子项，justify-content:center 把 650px 图表行撑到 ~1070px、整体右移 ~315px——Q3 柱/右侧柱组溢出卡片被裁。屏幕与 PDF 同症状（此前误判为打印竞态/裁剪，一轮像素级二分才定位：svg 计数、path getBBox、fill 检查全部通过，唯独 element 截图像素不通过）。｜已修：fallback 包 span 绝对定位铺满（脱离 flex 流）+ init 前移除；修复后 fig2 蓝像素 0→46,731、fig3 45k→127k，PDF pg3 蓝 3.6k→16.9k。教训：**DOM 结构断言 ≠ 渲染正确，图表验收必须做元素截图像素断言**；public/print-test.html 留作打印回归探针。
