---
name: ui-design-app
description: "Select, preview, audit, and apply an app UI style with packaged design systems. Use when the user explicitly invokes ui-design-app, asks to choose an app style, requests Finder/macOS or Linear styling, wants to remove a Web-like appearance, needs a UI design system, asks for a styled component/menu/popover, or plans a full-app visual restyle. Provides visual confirmation, tokens, materials, components, patterns, audits, and copyable CSS."
---

# ui-design-app：选风格 → 看演示 → 拿设计系统

## 目的

为新 app 或已有 app 确定 UI 视觉风格，并交付双主题 Token、材质、控件、布局交互规范和
可复制 CSS。回答“按什么风格做、长什么样、具体数值是什么”；不代替业务功能设计。

## 风格目录

| 风格 | 定位 | 成熟度 |
| --- | --- | --- |
| `finder` | macOS Finder：vibrancy、系统蓝、宽松密度、NSMenu | v1.0 |
| `linear` | SaaS 效率风：灰阶、品牌紫、紧凑密度、键盘优先 | v0.x |

推荐时只读 `references/style-catalog.md`。

## 执行原则

1. 并行执行互不依赖的只读检查；不要并行执行有先后依赖的修改。
2. 视觉确认只代表用户选定风格，不代表授权修改目标工程。
3. 新 app 定风格或大范围改风格必须经过 G1 视觉确认门和 G2 实施授权门。
4. 逐组件咨询不触发确认门，也不重复推荐风格。
5. 优先运行脚本并读取摘要；只在命中问题后加载对应规范章节。

## 工作流 A：新 app 选风格

### P1 · 并行收集

- 读取 `references/style-catalog.md`。
- 只读检查目标工程的平台、技术栈和现有主题入口；没有工程时忽略。
- 用户未给出平台、应用类型或气质偏好时，询问 1-2 轮简短问题；运行环境支持结构化输入时优先使用。

### P2 · 并行准备候选

- 用户点名风格时只准备该风格；不要绕过 G1。
- 用户未点名时准备 2-3 个候选；目录不足 3 个时展示全部可用候选。
- 并行打开候选 demo。需要同屏比较时运行：
  `python3 <skill>/scripts/generate-comparison.py finder linear --output /tmp/ui-style-preview`。
- 给每个候选呈现名称、一句话定位和相互差异。

### G1 · 视觉确认门

让用户肉眼确认 demo 或定制 mock。确认前不要开始大范围改码。

### G2 · 实施授权门

单独确认用户是否要求修改目标工程。若用户只需要推荐或规范，交付选择结果和资源路径后停止。

### P3 · 并行准备实施

获得实施授权后并行执行：

- 读取目标风格 `tokens.md` 与 `materials.md`。
- 盘点目标工程的全局样式、主题入口和组件层入口。
- 规划 CSS 拷贝位置；确认不会覆盖用户已有文件。

再按 Token → 窗口骨架 → 组件的顺序实施。复制 `tokens.css`；组件 CSS 按需复制。

## 工作流 B：已有 app 大范围改风格

1. 只读检查工程并读取 `references/audit-checklist.md`。
2. 运行 `python3 <skill>/scripts/audit-ui-style.py --project <project> --style <style> --format json`。
3. 在工具允许时并行补充四组检查：
   - P1-A：主题变量、写死色值、全局 CSS 污染。
   - P1-B：hover、active、disabled、focus-visible 状态。
   - P1-C：响应式、键盘、Esc 链、浮层定位。
   - P1-D：无障碍名称、语义角色、状态表达。
4. 合并为差距报告；不要把原始扫描输出全部放进上下文。
5. 把真实导航、工具栏与内容名称写成紧凑 JSON，运行
   `python3 <skill>/scripts/render-custom-preview.py --input <spec.json> --output /tmp/ui-style-preview/custom-preview.html`；
   小规格也可用 `--spec-json '<json>'`，避免创建中间文件；
   与差距报告并行生成目标态 mock。
6. 依次经过 G1 视觉确认和 G2 实施授权。
7. 按 Token → 全局 chrome → 单个区域 → 验证的顺序迁移；一个区域验证通过后再改下一区域。

## 工作流 C：开发中逐组件咨询

1. 从项目中的 tokens.css 或对话状态识别已选风格。
2. 只加载目标组件对应章节；例如菜单只读 `components.md` 菜单节和 `patterns.md` 菜单交互节。
3. 只改用户要求的组件，不重新推荐风格，不读取另一风格包。
4. Finder 浮层裁剪、Electron 拖拽区、fixed 定位或 Teleport 问题才读
   `references/styles/finder/engineering-electron.md`。

## 演示规则

- 内置 demo：`assets/styles/<style>/demo.html`，支持离线打开和亮暗切换。
- 对比页、定制 mock 写入临时目录，并告知用户可删除。
- 大范围迁移优先生成用户真实信息架构的 mock；通用 demo 只作兜底。
- 不要为了展示 demo 修改目标工程。

## 上下文预算

| 场景 | 最大加载范围 |
| --- | --- |
| 推荐 | `style-catalog.md` |
| 单组件 | 一个风格包内最多两个对应章节 |
| 窗口骨架 | `tokens.md` 相关章节 + `materials.md` + `patterns.md` §1-2 |
| 审计 | 先读脚本 JSON 摘要；命中规则后再读对应章节 |
| Electron 工程坑 | 仅命中相关问题时读 `engineering-electron.md` |

- 一次只加载一个风格包；用户换风格时明确说明上下文已切换。
- 长文件先查看章节索引，再读取目标章节。
- 不为确认一个变量读取完整组件 CSS；优先搜索变量定义。
- 不把可执行脚本源码或完整扫描日志加载进上下文，除非需要修脚本。

## 风格包契约与验证

```text
references/styles/<id>/ ：tokens.md、materials.md、components.md、patterns.md
assets/styles/<id>/     ：tokens.css、<id>-ui.css、demo.html
style-catalog.md        ：定位、适用、不适用、差异、成熟度
```

- 允许增加按需 reference，例如 Finder 的 `engineering-electron.md`。
- demo 必须离线可用、使用相对 CSS 路径、无构建和网络依赖。
- 修改风格包后运行：`python3 <skill>/scripts/validate-style-pack.py`。
- v0.x 允许 patterns 简化，但 tokens/components 必须可开发且声明未覆盖项。

## 定制参数

- 双主题都必须实现；允许选择默认亮/暗主题。
- 仅在风格包提供时允许选择密度档位。
- 主色属于风格身份：Finder 使用系统蓝，Linear 使用品牌紫；需要其他主色时定义新风格变体。

## 反模式

- 绕过 G1 或把 G1 当成实施授权。
- 只拷 CSS 不读状态语义。
- 跨风格混用材质、密度和交互语言。
- 手写重复的对比页或审计扫描，而不使用已有脚本。
- 修改 assets 后不运行风格包验证。

## 资源路由

- `references/style-catalog.md`：推荐矩阵。
- `references/audit-checklist.md`：迁移报告与审计流程。
- `references/styles/<style>/tokens.md`：颜色、排版、几何、动效。
- `references/styles/<style>/materials.md`：表面和材质。
- `references/styles/<style>/components.md`：控件状态与规格。
- `references/styles/<style>/patterns.md`：布局、交互和反模式。
- `references/styles/finder/engineering-electron.md`：仅 Electron/浮层工程问题。
- `assets/styles/<style>/`：可复制 CSS 与 demo。
- `scripts/generate-comparison.py`：确定性生成并排 demo。
- `scripts/audit-ui-style.py`：输出紧凑审计摘要。
- `scripts/validate-style-pack.py`：验证风格包契约与 CSS 变量。
- `scripts/render-custom-preview.py`：从紧凑 JSON 生成定制 mock。
