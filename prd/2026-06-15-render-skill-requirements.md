# 渲染 Skill 功能需求文档

> 产出自 `clarify-requirements` skill。**只描述"做什么功能"，不描述交互/UI/技术实现细节。**
> 技术机制（架构、扩展点实现、组件选型、脚本实现）一律记入"未决问题"，留给后续技术设计环节。

---

## 1. 一句话目标

一个读取**已校验的 `epps.json`**、把平台无关的页面规范渲染成**多平台（HTML / 安卓 XML / 安卓 Compose）高保真页面代码**、且架构上**可扩展新平台**的渲染 skill。

## 2. 目标用户

- **主要用户**：已用 `interaction-prototype` 拿到校验通过 `epps.json` 的产品 / 设计 / 前端 / 安卓开发。
- **次要用户**：需要快速预览同一份规范在多平台长什么样的团队成员。
- **不是**目标用户：
  - 还没有 `epps.json` 的人 —— 应先用 `interaction-prototype` 产出规范。
  - 需要可编译、可运行的完整工程的人 —— 本 skill 是预览级，不产出工程。

## 3. 核心场景

- **多平台预览**：拿到 `epps.json` → 选一套主题 → 产出 HTML + 安卓 XML + Compose → 各自预览，确认结构/层级/视觉一致。
- **HTML 演示**：用产出的自包含可点击 HTML 原型向团队/客户演示跳转与主次。
- **安卓起步代码**：安卓开发拿单页 `layout.xml` / `@Preview` Composable 作为页面结构起点。
- **扩展新平台**：后续要加 iOS / Flutter → 通过声明式接入，不改渲染核心。

## 4. 功能清单

### 模块：解析与渲染核心

| 优先级 | 功能 | 简述（做什么） | 验收标准（可判定） |
|--------|------|----------------|-------------------|
| P0 | `epps.json` 解析 | 读取并解析 prototype 级字段 + `pages[]` | 能正确读取 `sample_state`、`host_anchors`、每页 `zones`/`assistive_elements`/`jumps`；缺失必填字段时给出明确报错而非崩溃 |
| P0 | HTML 渲染 | 产出自包含、可点击的多屏 HTML | 双击即可打开；每屏对应一个 `page.id`；可按 `jumps` 点击跳屏；`legal_behavior`（如 submit/play_audio）点击有占位反馈 |
| P0 | 安卓 XML 渲染 | 每页一个 `layout.xml`，预览级 | 每个 `page` 产出一个 `layout.xml`；能在 Android Studio 预览面板渲染；使用 Material 语义组件；`onClick` 留空 stub |
| P0 | 安卓 Compose 渲染 | 每页一个 `@Preview` Composable，预览级 | 每个 `page` 产出一个 Composable + `@Preview`；能在 Android Studio 预览渲染；使用 Material3；可点元素留空 stub |
| P0 | 主次层级渲染 | primary 最强、secondary 降权、zone 按 priority | 三平台产物中 `primary_action` 视觉权重最强（唯一满宽 / 主色填充）；`secondary_actions` 降权（图标 / 描边 / 小尺寸）；同页不出现第二个等大主按钮 |
| P0 | `zone.kind` → 原生组件映射 | 14 种 `zone.kind` 映射到各平台语义组件 | 14 种 kind 全部有对应组件，HTML / 安卓各有映射表；遇到枚举外的 `kind` 报错而非静默跳过 |
| P0 | `element_contract` 承载 | 按 `intent`/`surface`/`priority`/`persistence` 渲染 | `intent: guidance` 不进主内容区；每页只有一个 `priority: primary` 的行动点；`surface` 与实际承载位置一致 |
| P0 | `sample_state` 插值 | 跨平台文案同源引用 `sample_state` | 三平台产物中同一示例值（年级 / streak / 进度 / 示例词）完全一致；`status` 字段正确插值，无跨平台漂移 |
| P0 | 跳转与行为落地 | HTML 可点；安卓仅视觉 | HTML 跳转可点、行为有占位反馈；安卓的跳转 / 行为渲染为"看得出来可点"的元素但不接真实逻辑 |

### 模块：视觉主题

| 优先级 | 功能 | 简述 | 验收标准 |
|--------|------|------|----------|
| P0 | 内置视觉主题 | 至少 1 套预设主题（配色 / 排版 / 圆角 / 阴影 token） | 三平台产物视觉风格一致；主 / 次层级通过 token 表达（primary 主色填充、secondary 降权） |
| P1 | 多套预设可切换 | 内置多套预设主题，渲染时选一套 | 至少 2-3 套预设；切换主题后三平台产物同步变化；token 跨平台一致 |

### 模块：质量保障

| 优先级 | 功能 | 简述 | 验收标准 |
|--------|------|------|----------|
| P1 | 跨平台投影对账 | 每平台产物 vs `epps.json` 的一致性校验 | 校验每平台产物的 zone 数量 / 顺序 / `kind`、跳转目标、主次权重与 `epps.json` 一致；不一致时报错并列出差异 |

### 模块：可扩展

| 优先级 | 功能 | 简述 | 验收标准 |
|--------|------|------|----------|
| P1 | 声明式新增平台 | 新增平台通过声明接入，不改渲染核心 | 新增一个平台渲染器时无需改动解析 / 主题 / 对账核心；首期 3 平台即以此可插拔结构落地 |

## 5. 明确不做（Out of scope）

- **不做可编译可运行的完整工程**：本 skill 是预览级，不产出 `build.gradle` / navigation graph / Activity 接线等工程骨架。
- **不做用户自定义外部 token 主题输入**：本期内置预设为主；外部 token 文件输入留后续。
- **不做新平台（iOS / Flutter / RN 等）的实际实现**：明确为后续，本期只保证架构可扩展。
- **不做真实业务逻辑 / 数据对接**：所有 `legal_behavior` 都是 stub / 占位反馈，不接真实评分、发音、提交等逻辑。
- **不做像素级 1:1 还原设计稿**：保结构 + 主次 + 视觉主题，非逐像素复刻某张高保真图。
- **不做需求变更 / 重新设计 `epps`**：只消费已校验的 `epps.json`；要改规范回上游 `interaction-prototype`。

## 6. 非功能约束

- **平台**：HTML + 安卓 XML + 安卓 Compose（首期）；架构须可扩展到更多平台。
- **输入**：已校验通过的 `epps.json`（schema 见 `skills/interaction-prototype/references/epps-schema.md`）。
- **一致性**：同一 `epps.json` + 同一主题 → 三平台产物的结构（zone / 跳转 / 主次）一致。
- **与上游解耦**：新 skill 有自己独立的 HTML 渲染，不依赖、不调用 `interaction-prototype`。

## 7. 未决问题（超出需求澄清范围，留给后续）

- **可扩展的具体机制**（插件 / 注册表 / 模板系统）：技术方案，留给后续技术设计。
- **多套预设主题具体是哪几套、token 字段格式**：设计细节，留给后续。
- **跨平台投影对账的实现方式**（可参考现有 `skills/interaction-prototype/scripts/audit_html_projection.py` 推广到安卓）：技术实现，留给后续。
- **14 种 `zone.kind` 到安卓 XML / Compose 的具体组件选择**（如 `hero_card` 在 XML 用什么布局、Compose 用什么 Composable）：组件映射细节，留给后续设计。
- **渲染 skill 的目录结构 / 产物落盘位置**：属工程组织，留给后续。
