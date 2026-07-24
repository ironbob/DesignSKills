# Lite / Full 报告格式

## Lite

Frontmatter：

```yaml
---
mode: lite
target: image-cache
title: 图片缓存机制快速分析
analyzed_at: 2026-07-24
covered_files:
  - src/cache.ts
chain_segments: 4
numerical_examples: 0
design_observations: 2
open_questions: 1
---
```

正文必须包含：

1. `## 机制概述`：对象、职责、主/次类型、分析置信度。
2. `## 范围与假设`：候选范围、工具降级、未确认假设。
3. `## 全链路`：3–6 个唯一的 `### STAGE-NN · 名称`，每段包含做了什么、怎么实现、设计依据、交接/最终效果、交接证据、实现证据。`observed` 另列“设计意图证据”；`unknown` 明确说明代码无法证明意图。
4. `## 数值示例`：有则使用 `### NUM-NN`；无则写“本机制未识别到需要工作示例的核心数值操作”。
5. `## 设计观察`：最多 3 个 `### OBS-NN`；每条包含需求来源、具体需求、为什么难、演进方向、代价/影响、置信度、证据。无则写“未识别到高相关设计观察”。
6. `## 已知缺口`。

每个阶段、数值示例和设计观察都必须至少包含一个回链。回链必须引用 frontmatter 的 `covered_files`，支持 `Makefile`、`Dockerfile` 等无扩展名文件，并使用有效行号。

## Full

Full Markdown 不手写。先完成 JSON，然后运行：

```bash
python3 scripts/render_report.py analysis.json analysis.md
```

渲染器生成：

- `mode: full` frontmatter
- 范围确认记录
- 机制概述与工具/证据置信度
- 按 JSON 顺序排列的全链路阶段
- 全部数值示例
- 架构、逻辑和跨阶段设计债
- 已知缺口

`validate_contract.py` 会重新渲染并要求 Markdown 与确定性结果完全一致。
`validate_report.py` 在存在 `mmdc` 时执行实际 Mermaid 渲染；缺少 `mmdc` 时只检查生成器安全子集，并把未实际渲染记入已知缺口。
