---
name: ui-design-app
description: "This skill should be used when the user explicitly invokes $ui-design-app / ui-design-app, or asks to '选 UI 风格', '给 app 定个风格', '做成 Finder/macOS 风格', 'Linear 风格', '界面太 Web 味想换风格', '按某风格做这个组件/菜单/弹层', '要一套 UI 设计系统', or is starting a new app / planning a large-scale UI restyle and needs a design system. It recommends 2-3 candidate styles by need, shows a visual demo for eyeball confirmation, then loads the chosen style's design system (tokens / materials / components / patterns + copyable CSS assets) to guide implementation."
---

# ui-design-app：选风格 → 看演示 → 拿设计系统

## 目的

为一个 app（新起或已有）确定一套 UI 视觉风格，并交付可落地的设计系统：双主题 Token、
材质配方、控件规格、布局与交互模式、可直接拷走的 CSS。回答一个问题：**这个 app 按
什么风格做，长什么样，具体数值是什么**。不回答"业务功能怎么设计"。

## 风格目录（首版两种）

| 风格 | 一句话定位 | 成熟度 |
| --- | --- | --- |
| `finder` | macOS 原生 Finder 观感：vibrancy 材质、系统蓝、宽松密度、NSMenu | v1.0（实战验证） |
| `linear` | 现代 SaaS 效率风：灰阶+单强调色、紧凑密度、键盘优先、无材质 | v0.x（可用级） |

推荐决策规则、适用场景矩阵、如何新增风格：读 `references/style-catalog.md`。

## 三个工作流

### A. 新 app 选风格起手

1. 用户点名风格 → 跳到第 4 步。未点名 → 按 **平台 / 应用类型 / 气质偏好** 问 1-2 轮（用 AskUserQuestion）。
2. 从目录选出 2-3 个候选，逐个给一句话定位与差异说明。
3. **演示确认门（硬性）**：向用户展示候选风格的演示页再请其确认——
   - 内置演示：`open <skill>/assets/styles/<风格>/demo.html`（浏览器打开，自带亮暗切换）。
   - 用户想对比时：生成一个并排对比页（两个 iframe 各引一份 demo），写入系统临时目录后 `open`。
4. 用户确认风格后：
   a. 拷贝 `assets/styles/<风格>/` 下的 CSS 进目标工程（tokens.css 必拷；组件层 CSS 按需）。
   b. 读该风格 `references/styles/<风格>/tokens.md` 与 `materials.md`，据此搭窗口骨架。
   c. 后续每个界面按 `components.md`（控件）与 `patterns.md`(布局/交互/反模式) 实现。

### B. 已有 app 改风格（大范围优化）

1. 按 `references/audit-checklist.md` 审计现状：全局 CSS、主题变量、控件尺寸/状态、反模式扫描。
2. 输出差距报告（模板在 checklist 内：区域/现状/目标/风险/工作量）。
3. **演示确认门（硬性）**：迁移前必须让用户看到目标态——优先按用户 app 的真实信息架构
   （真实导航项、真实工具栏动作）生成一张定制 mock 页（引风格包 CSS，写入临时目录 `open`），
   让用户肉眼确认后再动代码；通用 demo.html 作为兜底。
4. 分模块迁移：Token 落地 → 全局 chrome → 逐组件对齐规格 → 反模式清零复查。

### C. 开发中逐组件咨询

用户已定风格（或从工程里 tokens.css 的存在检测出风格）→ 只读该风格包中对应章节
（做菜单读 components.md 的菜单节 + patterns.md 的 NSMenu 交互节），**不重复推荐、不重读全包**。

## 演示确认门（规则汇总）

- 触发条件：新 app 定风格、大范围改风格。逐组件咨询不触发。
- 演示必须可肉眼确认：浏览器打开 HTML（macOS 用 `open`），不要只输出文字描述。
- 定制 mock 优于通用 demo：mock 用户自己的界面结构，确认的是"我的 app 变成这样"。
- mock/对比页写在临时目录（如 `/tmp/ui-style-preview/`），明确告知用户可随时删除。

## 风格包契约（新增风格必须满足）

```text
references/styles/<id>/ ：tokens.md、materials.md、components.md、patterns.md
assets/styles/<id>/     ：tokens.css、<id>-ui.css（组件层）、demo.html（自包含，引同目录 CSS）
style-catalog.md        ：追加条目（定位/适用/不适用/差异/成熟度）
```

- demo.html 必须离线可用（file:// 直开、CSS 相对路径引用、无构建无网络依赖）。
- 每包标注成熟度；v0.x 包允许 patterns 简化，但 tokens/components 必须完整可开发。

## 加载规则（渐进披露，勿全量读）

- 推荐阶段：只读 `style-catalog.md`。
- 确认后搭骨架：读 tokens.md + materials.md。
- 做具体界面前：按需读 components.md 或 patterns.md 的对应章节（文件内有分节标题，可先 grep）。
- 一次会话最多加载一个风格包的 references；用户中途换风格时明确说明 token 已切换。

## 定制参数（仅此两项，其余固定）

- 亮/暗主题默认值（双主题都必须实现，`[data-theme]` 切换）。
- 密度档位（若该包提供；finder 包 v1 仅常规档）。
- **主色不可改**：系统蓝/品牌紫是风格本体，改主色等于换风格。

## 反模式（skill 级）

- 未过演示确认门就开始大范围改码。
- 只拷 CSS 不读规范（数值背后的状态语义、单蓝规则会丢）。
- 跨风格混用（Finder 材质 + Linear 密度 = 两不像）。
- 修改风格包内 assets 时不同步 references（双源漂移）。

## 资源指针

- `references/style-catalog.md` — 风格矩阵、推荐规则、新增风格指南
- `references/audit-checklist.md` — 已有 app 审计流程与差距报告模板
- `references/styles/finder/` — tokens / materials / components / patterns（v1.0）
- `references/styles/linear/` — tokens / materials / components / patterns（v0.x）
- `assets/styles/finder/` — tokens.css、finder-ui.css、demo.html
- `assets/styles/linear/` — tokens.css、linear-ui.css、demo.html
