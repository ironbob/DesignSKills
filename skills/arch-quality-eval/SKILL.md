---
name: arch-quality-eval
description: "Trigger only when the user explicitly asks to use this skill by name: `$arch-quality-eval`, `arch-quality-eval`, or a namespaced form ending in `:arch-quality-eval`. Do not trigger from task similarity, refactoring or architecture keywords, repository contents, or inferred intent. Evaluate one JVM or C++ feature/subsystem for architecture smells and architecture readability, producing evidence-linked severity findings, refactor priority, and a gated go/no-go diagnosis."
---

# 架构质量评估：重构前诊断

只回答：**这个模块是否值得重构、阻塞点是什么、先改哪里**。输出机器事实源 `findings.json` 和由脚本生成的 `report.md`。不给完整重构方案，不做 lint、全仓巡检、CI 卡关或历史趋势。

## 不可跳过的门禁

在用户确认以下五项前，只做文件枚举和粗粒度结构识别，不深挖依赖、不定级、不写产物：

1. 路径；
2. JVM 或 C++；
3. 覆盖文件集合；
4. 是否手工喂入项目架构规约；
5. 一句话模块职责。

用户在首条请求中已明确给齐并声明确认时，直接通过此门。否则呈现范围并等待确认。禁止从代码现状推断“应有架构”，禁止编造证据；未实锤项标 `unconfirmed: true` 并登记 `known_gaps`。

最终交付必须通过四道门：

- `validate_findings.py`
- `validate_evidence.py`
- `validate_report.py`
- `validate_contract.py`

## 工作流

### 1. 圈定范围

读取 [scope-and-boundary.md](references/scope-and-boundary.md)。枚举 JVM/C++ 源文件，识别主体语言和粗结构，询问是否喂入规约，再执行范围确认门。

### 2. 生成共享事实索引

范围确认后读取 [analysis-protocol.md](references/analysis-protocol.md)。先探测 LSP；可用则用符号查询补强核心边，不可用则文本搜索降级并留痕。

运行预扫描器，避免每个分析轴重复遍历源码：

```bash
python3 <skill-dir>/scripts/scan_architecture.py <module-path> \
  --root <repo-root> --output <temporary-scan.json>
```

预扫描器只收集文件、包/命名空间、import/include、热点和 Git 协同变更线索，不直接判坏味道。C++ 在存在 `compile_commands.json` 与 clang 时自动增加 AST 语义边；可用 `--cpp-mode clang` 强制要求，否则失败时显式降级文本。以扫描结果定位热点，再读取必要源码验证语义。

### 3. 并行完成两个分析轨

共享同一份已确认边界、扫描结果和证据索引，并行执行：

- **轨 A：坏味道与规约** —— 读取 [arch-smells.md](references/arch-smells.md)，逐项判断核心五类及扩充类。仅当 `conventions_fed=true` 时再读取 [convention-checking.md](references/convention-checking.md)。
- **轨 B：架构可读性** —— 读取 [readability-assessment.md](references/readability-assessment.md)，评职责、依赖可理解性、命名表意、分层四轴。

可使用并行 agent 时，把轨 A、轨 B 分派为两个独立子任务；二者只返回候选 findings 和证据，不直接写最终文件。不可并行时，用批量搜索分别完成，避免重复读取同一文件。两个轨均不得越过确认边界。

### 4. 合并、分级和排序

读取 [severity-and-priority.md](references/severity-and-priority.md)。合并重复证据，填写 `severity_basis` 和 `priority_basis`，计算 critical/major/minor 与 go/no-go。

只在满足任一条件时运行建议性 LLM 裁判：

- 存在 critical；
- 存在 `unconfirmed: true`；
- 两个 finding 存在先决关系或 P1 排序冲突。

无上述情况时跳过裁判，避免无收益的第二遍推理。裁判不得新增事实。

### 5. 写唯一事实源并并行校验

读取 [findings-json-schema.md](references/findings-json-schema.md)，只由主分析者写：

`docs/arch-diagnosis/YYYY-MM-DD-<module>-findings.json`

JSON 必须显式包含范围、取证方法、核心五类覆盖状态、已知缺口、可读性总体结论、每条 finding 的分级依据和优先级依据。然后并行运行：

```bash
python3 <skill-dir>/scripts/validate_findings.py <findings.json>
python3 <skill-dir>/scripts/validate_evidence.py <findings.json> --root <repo-root>
```

任一失败即修 JSON 或证据并重跑，不进入报告阶段。

### 6. 自动渲染报告并并行验收

不要让模型手写 `report.md`。运行：

```bash
python3 <skill-dir>/scripts/render_report.py <findings.json> --output <report.md>
```

渲染后并行运行：

```bash
python3 <skill-dir>/scripts/validate_report.py <report.md>
python3 <skill-dir>/scripts/validate_contract.py <findings.json> <report.md>
```

只有修改渲染器或排查格式失败时才读取 [report-template.md](references/report-template.md)。报告校验或契约校验失败时，优先修 JSON；只有确定是渲染缺陷时才修脚本。

### 7. 交付

四道门全部通过后交付 JSON 与 Markdown，并说明：这是重构前诊断，完整重构设计留给后续阶段。

## 证据与质量纪律

- 以真实 `file:line`、类、函数或依赖边支撑每条 finding；证据必须位于 `covered_files`。
- 核心五类必须在 `core_smell_coverage` 中逐项写 `detected` 或 `not-detected`，且与 findings 一致。
- God Class、依赖密度等数值只作线索，最终依据职责和依赖语义。
- C++ 优先使用 compile database + clang AST，缺失时才以目录、命名空间和 include 文本近似；始终标明实际 backend 与剩余限制。
- 规约只接受用户手工输入；不自动解析架构文档或代码内 ArchUnit 等断言。
- 可读性只评架构语义，不评价缩进、命名格式、import 顺序等 lint 项。
- 改进只写方向，不写目标架构、完整迁移方案或实施步骤。

## 资源路由

| 阶段 | 必须读取 | 条件读取 |
|---|---|---|
| 范围确认 | `scope-and-boundary.md` | — |
| 共享取证 | `analysis-protocol.md` | — |
| 轨 A | `arch-smells.md` | `convention-checking.md`（仅喂入规约） |
| 轨 B | `readability-assessment.md` | — |
| 合并分级 | `severity-and-priority.md` | — |
| JSON 契约 | `findings-json-schema.md` | — |
| 报告 | 不读取，直接运行 renderer | `report-template.md`（仅排错/修改 renderer） |

脚本与示例可直接运行，不要为普通诊断把脚本源码或完整示例加载进上下文。脚本路径按本 `SKILL.md` 所在目录解析，不假设当前目录或 `${CLAUDE_PLUGIN_ROOT}` 固定存在。
