# Codex 风格 · 证据

## 采样范围

- `source-product`: OpenAI Codex desktop experience
- `source-version`: standalone Codex app Feb-Apr 2026; unified ChatGPT desktop shell from July 2026 tracked as a generation boundary
- `platforms`: macOS and Windows desktop
- `collected-at`: 2026-08-21
- `evidence-grade`: C+
- `representation`: standalone Codex task-workspace visual profile; not a claim of the full current ChatGPT desktop shell

## 官方来源

| ID | 官方来源 | 版本/日期 | 支持的结论 |
| --- | --- | --- | --- |
| O-CX-01 | [Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/) | 2026-02-02; Windows update 03-04 | 项目下组织 threads、多 agent 并行、thread 内 diff review、worktrees、Skills、Automations |
| O-CX-02 | [Codex for (almost) everything](https://openai.com/index/codex-for-almost-everything/) | 2026-04-16 | 多文件/终端、SSH、in-app browser、sidebar 文件预览、summary pane、长期任务 |
| O-CX-03 | [ChatGPT is now a partner for your most ambitious work](https://openai.com/index/chatgpt-for-your-most-ambitious-work/) | 2026-07-09 | Codex 进入统一 ChatGPT desktop shell；旧 Codex app 更新为新桌面 app，Chat/Work/Codex 共存 |
| O-CX-04 | [Using the built-in browser in the ChatGPT desktop app](https://help.openai.com/en/articles/20001277-using-the-built-in-browser-in-the-chatgpt-desktop-app) | 2026-08 采样 | 浏览器从 toolbar 打开，Chat/Work/Codex 共享桌面能力 |

## observed

- `O-CX-01` Codex 的稳定产品模型是 projects → separate threads，并在 thread 中查看改动、评论 diff、打开编辑器；worktree 隔离支持并行。
- `O-CX-01` Automations 的结果进入 review queue，Skills 有专门管理界面；这些是信息架构事实，不直接证明颜色、圆角或像素。
- `O-CX-02` 2026-04 后工作区扩展到多文件/终端、sidebar 预览、browser 和 summary pane，说明右侧/辅助面板可能因任务变化，不能固定成单一 inspector。
- `O-CX-03` 2026-07 后独立 Codex 外壳不再等同于当前完整桌面产品；Chat、Work、Codex 共用统一 shell。

## derived

- `D-CX-01` 安静中性色、受控阅读宽度、低对比边界、项目树、底部 composer 和克制浮卡来自已采样桌面截图/本地观察，不是 OpenAI 发布的设计 Token。
- `D-CX-02` 当前包的蓝色与墨黑用途、8-16px 圆角、120-160ms 反馈和面板尺寸均为视觉归纳。
- `D-CX-03` “右侧 inspector”是 standalone task-workspace 的一种组合；官方资料只支持 summary pane、files、terminals、browser 等上下文区域存在。

## adapted

- `A-CX-01` 非 AI/agent 产品保留自身对象模型，不新增 chat bubbles、composer、model picker、worktree 或 project/thread 层级。
- `A-CX-02` 长文优先阅读宽度；表格、画布或多文件产品可突破中心列，但保留安静层级和低噪 chrome。
- `A-CX-03` 统一 ChatGPT shell 与 standalone Codex profile 必须作为两个 generation 处理；未采样完整当前视觉前不混合组件。

## 视觉覆盖

| 默认骨架 | 交互状态 | 浮层 | 异常/边界 | 窄窗 | 主题 |
| --- | --- | --- | --- | --- | --- |
| 官方功能图/本地样本：部分 | 完整状态矩阵：缺 | project/menu/composer：derived | 长任务：功能有；视觉错误态缺 | 统一桌面/移动能力有；视觉样本缺 | 当前成对样本缺 |

## 证据缺口与禁止断言

- 官方发布页主要证明功能和信息架构，没有公开视觉 Token、全状态截图或组件规范，因此证据等级只能是 C+。
- 当前包不能宣称“2026-08 最新 ChatGPT/Codex 逐像素复刻”；它明确代表 standalone Codex task-workspace profile。
- 不得把项目树、composer、diff、终端或三栏结构迁移给没有同类功能的目标 app。

## 刷新条件

- 获得同版本统一桌面 shell 的宽窗、窄窗、主题和状态样本；OpenAI 发布桌面 UI 规范；Chat/Work/Codex 导航模型再次变化。
