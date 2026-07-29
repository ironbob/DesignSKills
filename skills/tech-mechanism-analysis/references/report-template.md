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
business_flow_steps: 4
sequence_messages: 3
architecture_roles: 3
boundaries: 4
behavior_cases: 3
acceptance_cases: 3
behavior_conflicts: 0
numerical_examples: 0
design_observations: 2
open_questions: 1
---
```

正文必须包含：

1. `## 机制概述`：对象、职责、主/次类型、分析置信度。
2. `## 范围与假设`：候选范围、工具降级、未确认假设。
3. `## 业务流程图`：流程图或外部 SVG/PNG，后附至少 2 个 `FLOW-NN` 步骤和 1 个 `FLOW-EDGE-NN` 流转；每项都含证据。
4. `## 时序图`：时序图或外部 SVG/PNG，后附至少 2 个 `PARTICIPANT-NN` 参与者和 1 个 `MESSAGE-NN` 消息；每项都含证据。
5. `## 架构角色图`：角色图或外部 SVG/PNG，后附至少 2 个 `ROLE-NN` 角色和 1 个 `ARCH-EDGE-NN` 关系；角色包含实体类型、具体职责，且每项都含证据。
6. `## 全链路`：3–6 个唯一的 `### STAGE-NN · 名称`，每段包含做了什么、怎么实现、设计依据、交接/最终效果、交接证据、实现证据。`observed` 另列“设计意图证据”；`unknown` 明确说明代码无法证明意图。
7. `## 必检边界覆盖`：取消、异常、并发、背压各自映射到同类 `BOUNDARY-NN`。
8. `## 边界清单`：至少一个 `### BOUNDARY-NN · 名称`，包含类别、适用性、处理能力、条件、期望契约、实际行为、验证状态、关联行为用例和源码锚点。
9. `## 可验证行为用例`：至少一个 `### CASE-NN · 名称`，字段按 `references/case-analysis.md`，包含语义条件键、源码锚点和验收用例引用。
10. `## 验收用例`：至少一个 `### ACCEPT-NN · 名称`，包含关联行为用例、Given、When、Then、验证级别和源码锚点。
11. `## 多入口/分支行为矛盾`：有则使用 `### CONFLICT-NN`；无则写“未识别到多入口/分支行为矛盾”。
12. `## 数值示例`：有则使用 `### NUM-NN`；无则写“本机制未识别到需要工作示例的核心数值操作”。
13. `## 设计观察`：最多 3 个 `### OBS-NN`；每条包含需求来源、具体需求、为什么难、演进方向、代价/影响、置信度、证据。无则写“未识别到高相关设计观察”。
14. `## 已知缺口`。

每个阶段、边界（`not-applicable` 除外）、行为用例、验收用例、矛盾记录、数值示例和设计观察都必须至少包含一个回链。回链必须引用 frontmatter 的 `covered_files`，支持 `Makefile`、`Dockerfile` 等无扩展名文件，并使用有效行号。

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
- 在全链路之前生成业务流程图、时序图和架构角色图，以及对应的结构/职责证据清单
- 边界清单、可验证行为用例及对应验收用例
- 多入口/分支行为矛盾，或在已覆盖范围内明确未发现
- 全部数值示例
- 架构、逻辑和跨阶段设计债
- 已知缺口

`validate_contract.py` 会重新渲染并要求 Markdown 与确定性结果完全一致。
`validate_report.py` 强制检查三图的章节顺序、类型、节点/参与者/角色、边/消息/关系、职责清单和证据。
PATH 中存在 `mmdc` 时尽力实际渲染；环境缺失、渲染失败或超时只输出非阻塞
提示，但三图的结构门禁始终阻塞。外部 SVG/PNG 回退可在对应 JSON 图对象中
加入 `artifact`，也必须保留完整结构清单。
