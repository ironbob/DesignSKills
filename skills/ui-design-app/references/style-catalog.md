# 风格目录（style catalog）

> 推荐阶段的唯一读取物。每条目 = 推荐决策需要的全部元信息。

## 推荐决策规则

1. 先确认四个信号：**平台**（macOS / 跨平台 / Web）、**应用类型**（效率工具 / 内容浏览 / 管理后台 / 创作工具）、**内容与交互形态**（列表 / 表格 / 树 / 画布 / 长文，鼠标 / 键盘）、**气质偏好**（原生融入 vs 独立品牌感 / 宽松 vs 紧凑）。
2. 按下表匹配；命中多个时取 2-3 个候选给用户选，并在演示页上肉眼对比。
3. 用户描述含明确风格名（"像 Finder""像 Linear"）→ 直通该风格，不再推荐；仍要判断来源布局是否兼容。
4. 推荐的是设计语言，不承诺复制来源 app 的业务结构。默认保留目标产品布局；不兼容项按 `style-transfer-model.md` 标记 N/A。

## 风格矩阵

### finder —— macOS 原生 Finder 观感

| 维度 | 内容 |
| --- | --- |
| 定位 | 让 app 看起来是 macOS 系统一员：系统材质/Liquid Glass、用户 accent、平台菜单语言、窗口失活降级 |
| 适用 | macOS 优先的桌面工具（文件/设备/媒体/编辑器类）；追求"原生感、无 Web 味"的任何桌面 app |
| 关键词 | 原生、材质、毛玻璃、系统蓝、Finder、宽松、鼠标优先 |
| 不适用 | 品牌驱动的产品站/SaaS 后台；需要强品牌色的 app（主色锁定系统蓝）；键盘重度效率流（密度偏松） |
| 与 linear 的核心差异 | 系统材质 vs 生成式实色主题；用户系统 accent vs 每主题单一产品 accent；更宽松的平台控件 vs 更紧凑的命令型 chrome |
| 成熟度 | v1.0（来自一个完整 Electron 应用的全量实战与三轮审计） |
| 证据 | B；macOS Tahoe 26 Finder/HIG，精确 CSS 数值为 derived，见 `styles/finder/evidence.md` |
| 演示 | `assets/styles/finder/demo.html` |

### linear —— 现代 SaaS 效率风

| 维度 | 内容 |
| --- | --- |
| 定位 | Linear 效率工具风：中性灰阶 + 每主题单一可配置 accent、紧凑列表、键控交互、快速微动效 |
| 适用 | Web app / SaaS 后台 / 项目与任务工具 / 开发者工具；键盘优先的高频操作流 |
| 关键词 | 紧凑、灰阶、单 accent、键盘优先、命令面板、⌘K、效率 |
| 不适用 | 追求 OS 原生融入的桌面 app（无材质、无 NSMenu）；休闲/内容消费类（密度过高显严肃） |
| 与 finder 的核心差异 | 实色生成主题 vs 系统材质；可配置 accent vs 用户系统 accent；更紧凑、命令/键盘入口更强 |
| 成熟度 | v0.x（可用级：tokens/components 完整，patterns 简版，未经实战打磨） |
| 证据 | B+；2024 foundational redesign + 当前官方交互 Docs，px/hex 为 derived，见 `styles/linear/evidence.md` |
| 演示 | `assets/styles/linear/demo.html` |

### things —— Things 3 清爽产品风（classic / OS 26）

| 维度 | 内容 |
| --- | --- |
| 定位 | macOS 清爽产品风：白净内容 + Things 蓝、大标题、大留白、圆形完成控件、宽松行距；classic 为实色，3.22/OS 26 在侧栏和按钮加入克制 glass |
| 适用 | macOS 优先的消费者工具（任务/笔记/日历/阅读/习惯类）；追求"干净愉悦"、以亮色为人设默认的 app |
| 关键词 | 白净、大留白、宽松、圆形复选框、区域色点、大标题、Things 蓝、鼠标优先、柔和动效 |
| 不适用 | 数据密集后台（密度太松）；键盘重度效率流（快捷键默认隐藏）；以深色为人设的产品 |
| 与 finder 的核心差异 | 独立品牌 vs 系统一员；Things 蓝、白净内容、宽松行与完成反馈优先。OS 26 可有少量 glass，但不扩散到内容画布 |
| 成熟度 | v0.x（可开发；classic 完整，OS 26 材质差异已证据化但仍需更多状态样本） |
| 证据 | B；Things 3 官方 features + Things 3.22/OS 26 官方更新，数值为 derived，见 `styles/things/evidence.md` |
| 演示 | `assets/styles/things/demo.html` |

### geist —— Vercel dashboard / Geist monochrome profile

| 维度 | 内容 |
| --- | --- |
| 定位 | 完整 Geist 设计系统中的 Vercel dashboard 单色配置：中性骨架 + 黑白反转主操作 + 真黑暗色 + 等宽点缀；状态按 Geist 语义色阶表达 |
| 适用 | Web 仪表盘 / 管理后台 / 开发者工具 / infra·部署·监控·分析类数据密集 SaaS |
| 关键词 | 单色系、黑主按钮、真黑、等宽点缀、状态 pill、键值设置行、表格、⌘K |
| 不适用 | 需要大面积品牌彩色表达的产品；内容消费/创作工具；macOS 原生融入需求。需要完整 Geist 彩色组件时不要受本单色 profile 限制 |
| 与 linear 的核心差异 | 黑白反转主操作 vs 单 accent 主操作；中等密度与机器信息 mono vs 更紧凑、动作快捷键更突出 |
| 成熟度 | v0.x（可开发；已纠正为 Geist 的单色 profile，尚未自动绑定 Geist Core Token） |
| 证据 | B+；当前 Geist foundations/components/guidelines，离线 hex 为 derived，见 `styles/geist/evidence.md` |
| 演示 | `assets/styles/geist/demo.html` |

### figma —— Figma 创作工具风

| 维度 | 内容 |
| --- | --- |
| 定位 | 正式 Figma UI3 的专业创作工具 chrome：中灰画板 + 可折叠/可调宽停靠面板 + 底部 slim toolbar、微型控件、选中蓝画布语义 |
| 适用 | 创作/编辑工具（设计器、编辑器、建模、白板、画布类）；"画布 + 面板"结构的任何专业工具 |
| 关键词 | 停靠面板、底部工具条、灰画板、微型控件、图层树、属性面板、单键工具、最紧凑 |
| 不适用 | 列表/详情型效率工具（无画布语义）；消费者休闲产品（密度过高）；文档阅读类 |
| 与 linear 的核心差异 | 画布+可收起停靠面板 vs 导航/内容视图；选择蓝作用于画布对象与手柄；键盘以工具模式为主而非全局动作列表 |
| 成熟度 | v0.x（可开发；已按正式 UI3 修正面板与工具条代际，数值仍待测量） |
| 证据 | B+；UI3 官方 redesign/transition/retrospective，见 `styles/figma/evidence.md` |
| 演示 | `assets/styles/figma/demo.html` |

### codex —— standalone Codex task-workspace profile

| 维度 | 内容 |
| --- | --- |
| 定位 | 2026-02 至 04 standalone Codex 的安静任务工作区 profile：极浅中性层级、项目/线程、居中任务流、可变上下文区域、底部输入台。 |
| 适用 | AI 工作台、研究/写作/代码协作工具、带项目上下文的桌面效率应用；需要“专注内容但随时可见上下文”的产品。 |
| 关键词 | 安静、工作区、项目树、居中列、检查器、低对比边界、圆角浮卡、输入台、蓝色未读点。 |
| 不适用 | 数据密集监控台（信息密度不足）；强品牌营销产品；画布型创作工具（没有 Figma 的画布语义）。 |
| 与 finder 的核心差异 | 同为桌面感：Codex 以实色/轻阴影表达层级，不依赖振动材质；导航是项目与会话树，主内容为阅读宽度受控的任务流；右侧检查器是上下文而非文件属性。 |
| 与 linear 的核心差异 | 同为效率工具：Codex 更宽松、主内容居中并允许长文；高频项不用 kbd chip 装饰；选中是中性灰底，蓝色只标记链接、未读和焦点。 |
| 成熟度 | v0.x（可开发；已锁定 standalone 代际，不能冒充 2026-07 后统一 ChatGPT desktop shell）。 |
| 证据 | C+；官方资料强支持信息架构，但视觉 Token/完整状态证据不足，见 `styles/codex/evidence.md` |
| 演示 | `assets/styles/codex/demo.html` |

## 候选卡片呈现要求

用结构化用户输入或简短文字给候选时，每张卡片必须含：风格名 + 一句话定位 + 与其他候选的
一句差异 + demo 路径提示（"已为你打开演示页"）。**不要**只给风格名让用户盲选。

## 如何新增风格

1. 建 `references/styles/<id>/` 六件套（含 `identity.md`、`evidence.md`）与 `assets/styles/<id>/` 三件（契约见 SKILL.md）。
2. demo.html 必须离线自包含；CSS 数值与 references 完全一致（demo 是规范的活样张）。
3. 在本文件矩阵追加条目，标注成熟度 v0.x。
4. `evidence.md` 先锁定版本、平台、官方来源和 observed/derived/adapted；`identity.md` 再区分 invariant / adaptive / archetype-bound / source-specific。
5. 没有同版本一手视觉证据的风格长期停留在 v0.x，且证据等级不得高于 C。
