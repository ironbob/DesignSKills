# deviations · 执行偏差日志（全流程持续记录）

| # | 阶段 | 偏差/决策 | 内容 | 处置 |
|---|---|---|---|---|
| 1 | 5P | 环境定位 | skill 由 `~/.claude/skills` 发起，渲染底座实际在 `/Users/wtb/work_space/DesignSkills/`（仓库根） | 以 DesignSkills 为仓库根执行全部 gate 与构建 |
| 2 | 4 | gate 修复 | 04 表"内容类型"列写成 `T6 分类数值` 带名称后缀，check_plan 要求纯 `T\d+` | 列值归一为 T 编号，目录名移入表头说明 |
| 3 | 6P→8P | 底座缺陷修复 | check-storyboard 白名单正则无 `g` 标志：同一字符串第二个日期/月份引用不被吞掉（"1 月–6 月"只剩"6"误判裸数字） | 底座修复：白名单替换改全局正则（ppt-renderer/checks/check-storyboard.mjs），三处合法日期范围放行 |
| 4 | 6P | 底座扩展 | metricsBar 基期类目硬编码 `'25 H1'`，与本文档口径（改造前/沉淀前）不符 | 底座扩展：`spec.catLabels` 可选参数（向后兼容，默认不变），P3 用 [改造前/改造后]、P6 用 [沉淀前/当前] |
| 5 | 8P | 底座扩展 | decision-ask 版式 `slice(0, 2)` 只渲染两张请求卡，brief 要求 ≤3 条规划，第三条会被静默丢弃（QA 不报错——覆盖率黑洞） | 底座扩展：≥3 请求时走 compact-3 分支（三张 0.98in 紧凑卡：事项/目标+基线/资源+Owner+截止 三行），六字段数据仍全量校验；storyboard 文案按框容量收敛 |
| 6 | 8P | 文案收敛 | 首轮 check-slides 10 处"文字超出框高"（估算折行）：标题 >27 字符单位、风险条 >25、risk/action what >20、请求行超一行 | 按各框容量（标题 23pt 单行 ≈27 CJK 单位等）逐处缩短，语义保留（"一个里程碑延期 1 周"→"里程碑延期 1 周"），详句下沉 notes |
| 7 | 9P | 视觉复核方式 | 本环境 Read 图片走 CDN 转链不可直读 | zai-mcp 逐页读图复核（同前次 h1-mkt-ops 运行惯例），pdftotext 数字交叉验证 |
