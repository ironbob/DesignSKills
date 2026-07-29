---
name: tech-mechanism-analysis
description: "Trigger only when the user explicitly asks to use this skill by name: `$tech-mechanism-analysis`, `tech-mechanism-analysis`, or a namespaced form ending in `:tech-mechanism-analysis`. Do not trigger from task similarity, mechanism-analysis keywords, repository contents, or inferred intent. Traces one technical mechanism from entry to effect in lite or full mode, requiring validated business-flow, sequence, and architecture-role diagrams before the detailed analysis, plus evidence-backed explanations, boundary inventories, verifiable behavior and acceptance cases, conflict records, and, in full mode, validated machine- and human-readable artifacts."
---

# 技术机制分析

分析代码库中的**一个技术机制**，回答：

1. 它如何从入口运行到最终效果？
2. 哪些设计选择会让真实或合理的未来需求变难？

始终区分**代码事实、分析推断、未知设计意图**。不要把函数名、注释或假设写成已经证实的结论。

## 选择模式

先加载 `references/modes.md`。

- 用户明确指定 `lite` / `full` 时服从用户。
- 用户未指定时默认 `lite`。
- 用户要求“深度、完整、正式、可审计、设计债审计、JSON 契约、全部数值环节”时选 `full`。
- 开始工作时声明所选模式和原因；用户可随时切换。

## 共同边界

只分析单个机制。整体架构评估、业务逻辑反推、正确性 bug 复现、完整重构方案和新功能编码不在本 skill 范围。

共同质量要求：

- 从入口追到最终效果；真实链路允许分支、循环、并发和混合机制，不强塞线性模板。
- 在详细文字分析前强制给出**业务流程图、时序图、架构角色图**。三个图回答不同问题，均须包含源码证据；架构角色图必须明确具体类/模块/服务的职责。默认使用 Mermaid，交付环境不支持时按 `references/required-diagrams.md` 使用 Graphviz/PlantUML 等工具导出的 SVG/PNG。
- 每个关键事实回链 `file:line`；找不到依据时标记 `⚠ 未确认`。
- `why` 必须标记依据：`observed`（有明确证据）、`inferred`（分析推断）或 `unknown`（代码无法证明）。
- 数值示例必须按原代码逻辑计算；保留单位、精度、分支、clamp、溢出等影响结果的步骤。
- 主动枚举协议兜底：空输入、上下界、结束哨兵、取消/异常、非法状态和动态解析失败；取消、异常、并发、背压必须出现在独立必检覆盖清单。背压审计回指 `flow-control` 条目，其余回指同名边界。分别记录适用性、处理能力和验证状态；无界队列表示背压能力 `unsupported`，不是“存在背压”。存在实现分支时至少给一个可运行或可复核的边界示例，不只验证 happy path。
- 输出边界清单，并把每个关键边界串到可验证行为用例、源码锚点和对应验收用例。行为用例与验收用例必须双向可追溯。
- 比较同一机制的多入口和关键分支；只有 `semantic_key` 相同的语义条件出现互不兼容的返回、异常、状态、副作用或时序时才记录矛盾。左右越界等不同边界语义不是矛盾。没有发现也要在已覆盖范围内明确说明。
- 设计债不是 bug。每条必须说明具体需求、需求来源、为什么难、演进方向、代价和结论置信度。
- “未识别到设计债”是合法结论，不为凑双轴而制造问题。

按需加载：

- 范围与置信度：`references/scope-and-boundary.md`
- 机制类型与链路：`references/mechanism-type-templates.md`
- 代码取证：`references/analysis-protocol.md`
- 数值示例：`references/numerical-worked-example.md`
- 设计债：`references/design-debt-audit.md`
- Full JSON：`references/analysis-json-schema.md`
- Lite/Full 报告：`references/report-template.md`
- 三张必检图：`references/required-diagrams.md`
- 非线性验证矩阵：`references/validation-matrix.md`
- 边界、行为用例、源码锚点、验收用例与矛盾记录：`references/case-analysis.md`

## Lite 工作流

1. 根据用户给出的机制名、入口和根路径形成**候选范围**。无需例行等待确认；只有存在多个实质不同的解释且选错会改变结果时才询问。
2. 识别主机制类型和必要的次类型，选择 3–6 个能解释真实链路的阶段。
3. 沿链路读取关键文件，记录事实、调用边、数据/状态变化、时序、边界和最终效果。
4. 按 `references/required-diagrams.md` 先画业务流程图、时序图和架构角色图，并完成步骤、流转、参与者、消息、角色、关系清单与证据回链；不得先写全链路正文再补图。
5. 按 `references/case-analysis.md` 输出边界清单、可验证行为用例、源码锚点、对应验收用例，并比较多入口/关键分支的行为契约。
6. 对理解机制必需的核心数值操作给工作示例；不展开无关的下标或简单计数。
7. 最多给 3 条高相关设计观察。没有用户路线图时把需求来源标为 `hypothetical`，不要把假设包装成必然债务。
8. 按 `references/report-template.md` 写一份 `mode: lite` Markdown。默认保存到：
   `docs/mechanism-analysis/YYYY-MM-DD-<target>-lite.md`。
9. 运行：

```bash
python3 <skill-dir>/scripts/validate_report.py <lite.md> --root <repo-root>
```

校验通过后交付。用户明确只要聊天回答时，可不写文件，但仍遵守 Lite 结构与证据纪律。

## Full 工作流

1. 形成**候选范围**：机制对象、主/次类型、候选覆盖文件、工具与证据置信度、一句话职责。
2. 把候选范围呈现给用户确认。此时的文件集合是候选集，不宣称完整。
3. 把确认动作写入 `scope_confirmations`。沿真实链路追踪；若发现新语言、新根目录、新入口或不同最终效果，视为**实质扩围**，更新范围、再次确认并追加记录。同目录辅助文件可直接继续并在报告记录。
4. 按 `references/required-diagrams.md` 先建立 `diagrams.business_flow`、`diagrams.sequence` 和 `diagrams.architecture_roles`。三图全部通过 JSON 与报告门禁后，才进入详细文字分析。
5. 逐阶段说明 what/how/why/why_basis、关键结构、handoff 和各自证据。`observed` 必须提供直接设计意图证据；`unknown` 必须明确说明代码无法证明。模板与阶段按顺序一一对应。
6. 主动复核所有数值环节是否正确标记 `numerical`，并为每个 `numerical=true` 阶段提供至少一个忠实数值示例；把空输入、上下界和其他协议短路纳入示例或运行验证。
7. 按 `references/case-analysis.md` 建立边界 → 行为用例 → 源码锚点 → 验收用例追溯链；枚举已覆盖入口和关键分支，记录真实矛盾或明确未发现。
8. 审计架构轴、逻辑轴和跨阶段衔接。每条设计债写明：
   `requirement_source`、`hard_requirement`、`why_hard`、`evolution_direction`、
   `cost_impact`、`cost_quantification`、`confidence`、`confidence_basis`。
9. 人工复核每条证据和源码锚点是否真正支持相应结论。脚本只验证结构、文件、行号和有限的近邻线索，不能替代语义复核。
10. 为三张必检图生成安全子集 Mermaid；交付环境不支持 Mermaid 时，在 JSON 中声明由 Graphviz、PlantUML、Structurizr 等工具导出的 SVG/PNG。PATH 中存在 `mmdc` 时尽力实际渲染 Mermaid。缺少环境、渲染失败或超时不阻塞，但三图的结构、类型、职责和证据校验必须通过。
11. 先写 `analysis.json`。不要手写 Full Markdown。
12. 依次运行：

```bash
python3 <skill-dir>/scripts/validate_analysis.py <analysis.json>
python3 <skill-dir>/scripts/validate_evidence.py <analysis.json> --root <repo-root>
python3 <skill-dir>/scripts/render_report.py <analysis.json> <analysis.md>
python3 <skill-dir>/scripts/validate_report.py <analysis.md> --root <repo-root>
python3 <skill-dir>/scripts/validate_contract.py <analysis.json> <analysis.md>
```

任一道失败都先修复再交付。Full 默认输出：

- `docs/mechanism-analysis/YYYY-MM-DD-<target>-analysis.json`
- `docs/mechanism-analysis/YYYY-MM-DD-<target>-analysis.md`

## 禁止事项

- 不把注释复述、函数名释义或空泛措辞当作分析。
- 不把 `why` 推断写成作者已确认的设计意图。
- 不把假想需求写成确定会发生的需求。
- 不用 `critical/major/minor` 给设计债分级；`confidence` 表示证据可信度，不是严重度。
- 不在 Full 模式手工维护 JSON 和 Markdown 两份事实。
- 不因 LSP 不可用而例行阻塞；自动降级到可用的搜索/编译/测试工具，并如实降低置信度。

## 终态

- Lite：一份证据可达、结构完整、校验通过的 Markdown，或用户明确要求的等价聊天回答。
- Full：验证通过的 JSON + 由 JSON 确定性生成的 Markdown。

格式示例见 `examples/2026-07-24-example-lite.md` 和
`examples/2026-07-23-example-analysis.json`。异步、状态机和反射的 Full
验证样例及运行命令见 `references/validation-matrix.md`。
