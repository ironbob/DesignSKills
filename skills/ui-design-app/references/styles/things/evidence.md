# Things 风格 · 证据

## 采样范围

- `source-product`: Cultured Code Things
- `source-version`: Things 3 classic baseline plus Things 3.22 / OS 26 material delta
- `platforms`: macOS; iOS/iPadOS only as cross-platform motion evidence
- `collected-at`: 2026-08-21
- `evidence-grade`: B
- `representation`: classic-solid default; OS 26 glass is a documented optional material profile

## 官方来源

| ID | 官方来源 | 版本/日期 | 支持的结论 |
| --- | --- | --- | --- |
| O-TH-01 | [Things features](https://culturedcode.com/things/features/) | Things 3 launch baseline | 白色 todo sheet、结构化内容、平滑动效、Today/Upcoming、headings、checklists、Magic Plus、Slim Mode |
| O-TH-02 | [Things for OS 26](https://culturedcode.com/things/blog/) | Things 3.22, 2025-09-15 | 更宽松间距、曲率更新、侧栏少量 glass、glassy buttons 的 glow/scale、Magic Plus 液态形变 |
| O-TH-03 | [Quick Find](https://culturedcode.com/things/support/articles/2803584/) | 当前支持文档 | 直接键入/⌘F 的浮层查找与快速导航 |
| O-TH-04 | [Hiding the sidebar](https://culturedcode.com/things/support/articles/3238254/) | 当前支持文档 | Slim Mode/侧栏可折叠与窗口适配 |

## observed

- `O-TH-01` Things 3 的长期身份是清晰白色内容、结构化信息、较少干扰、平滑且愉悦的交互。
- `O-TH-01` 圆形完成控件、Today/Upcoming、headings、checklists、Magic Plus 是任务产品语义，其中只有形态和反馈可迁移。
- `O-TH-02` Things 3.22 在 OS 26 上不再是“绝对无玻璃/无缩放”：侧栏有少量 glass，按钮有轻微 glow 与 scale，间距更宽、曲率更新。
- `O-TH-03`、`O-TH-04` Quick Find 和 Slim Mode 证明其界面同时重视直接操作、键盘快速导航与空间回收。

## derived

- `D-TH-01` Things 蓝、40-44px 行、22px 标题、圆角与 150-250ms 时长是本包的视觉估算，不是 Cultured Code 公布的 Token。
- `D-TH-02` classic profile 使用白净实色侧栏；os26 profile 只在 sidebar/chrome 使用克制半透明，不把内容画布玻璃化。
- `D-TH-03` 区域色点的具体七色值是风格化映射；官方资料只支持存在清单/区域组织，不支持这些 hex 为官方值。

## adapted

- `A-TH-01` 非 OS 26、Web 或性能受限环境默认使用 classic-solid；支持背景采样的平台可选择 os26-glass，并提供实色 fallback。
- `A-TH-02` glow/scale 只用于明确可按压的高价值小控件，幅度极小，并在 `prefers-reduced-motion` 下关闭。
- `A-TH-03` 完成圆圈只迁移给 checkbox/完成语义；普通 switch、单选和主按钮保持其正确控件语义。

## 视觉覆盖

| 默认骨架 | 交互状态 | 浮层 | 异常/边界 | 窄窗 | 主题 |
| --- | --- | --- | --- | --- | --- |
| classic 与 OS26 Mac 图：有 | 完成/Magic Plus：有；focus/disabled 缺 | Quick Find：有 | 长清单：部分；错误/加载缺 | Slim Mode：有 | OS26 多外观存在；Mac 全状态样本不足 |

## 证据缺口与禁止断言

- 当前 assets 不是 Cultured Code 官方资源，像素、颜色和动效曲线均未获得官方 Token 级验证。
- 不能同时声称“当前 Things 3.22”与“完全无 glass/无 scale”；选择 classic 时必须在交付中标明版本风格。
- 不得将 Inbox、Today、Upcoming、This Evening 或 todo 布局强加给非任务产品。

## 刷新条件

- Things 3.23/OS 27 发布视觉更新；Cultured Code 公布设计 Token；目标平台 Liquid Glass 行为变化。
