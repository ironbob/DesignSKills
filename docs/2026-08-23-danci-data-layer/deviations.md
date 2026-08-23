# 干跑/执行偏差日志（deviations）——本文档执行期记录

格式：D-编号｜阶段｜偏差｜处置。

- **D-001**｜S5｜markdown 组件/围栏写进裸 `<div>` 后经 html_block 解析变成平级 token，浏览器把后续内容全部吞进第一个 div（第二档嵌进第一档、并排布局坏）。｜对比页改为**单页切换式**：同一内容渲染一次，页内按钮热切换 `body[data-doc-preset]`，副作用（SSR 期 document 不存在）以 `typeof document` 守卫 + `onUnmounted` 清理兜住。
- **D-002**｜S5｜md 内 `<script setup>` 按纯 JS 解析，`(p: string) => {}` TS 注解导致 babel 构建报错。｜md 内 script 一律写纯 JS（数据层 .ts 文件不受影响）。
- **D-003**｜S5｜`npm run dev` 下 fastdom ESM 互操作错误导致 app 不挂载（金标准 q3 页同样症状），dev 不可用于验证。｜验证路径一律 build+preview（与金标准验证记录一致）。
- **D-004**｜S5｜KpiRow 字号硬编码 48px/20px，档位变量无法穿透 scoped 样式。｜改为 `var(--doc-kpi-num-size, 48px)` / `var(--doc-kpi-unit-size, 20px)`（可主题化最小改动，非结构变更）。
- **D-005**｜S5｜历史残留 preview 进程占用端口，浏览器看到旧产物（新构建已写入 dist）。｜排查先 `ps aux | grep vitepress`，杀残留后换新端口重启。
- **D-006**｜S5｜底座为亮色专用（--doc-card 等按亮色定义），Playwright 误触外观按钮进暗色导致截图像素异常。｜截图前显式确认 `html.dark` 不存在并写 localStorage 锁 light。
- **D-007**｜S7/S8｜`check_doc --md` 把 `<script setup>` 内联块当 189 字段落误报 WALL WARN。｜script 块内加空行分段（各段 <180 字）消除，无需改 gate；可回填 skill：MD_PROSE_SKIP 增加 script 围栏识别。
- **D-008**｜S8｜「17–65%」「61–65%」区间概括原不在台账，违反「新数字先回填」红线。｜已回填 F-24（推算档，注明派生方法）；此类极值区间概括在成稿期高发，skill 阶段 7 卡可加一条「区间概括=新数字」提醒。
- **D-009**｜S8｜s4 对比矩阵行列取向与 T5 模板（列=候选/行=维度/含权重）不一致。｜按金标准语料取向豁免并记录 08-findings；若评审会要权重打分再回 04 改形式。
- **D-010**｜S8｜PDF 验收无法逐页渲染（无 fitz/pdftoppm），页面级像素断言缺工具。｜改用 PDF 内容流矢量断言（accent rg 填充 27 处）+ pdftotext 文本完整性双线索；建议底座补一个 PDF 验收脚本位。
