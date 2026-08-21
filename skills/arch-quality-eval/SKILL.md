---
name: arch-quality-eval
description: "Trigger only when the user explicitly asks to use this skill by name: `$arch-quality-eval`, `arch-quality-eval`, or a namespaced form ending in `:arch-quality-eval`. Do not trigger from task similarity, refactoring or architecture keywords, repository contents, or inferred intent. Evaluate one JVM or C++ feature/subsystem using architecture design principles inspired by Code Complete 2, producing evidence-linked findings, honest coverage/confidence, refactor priority, and go/no-go/inconclusive diagnosis."
---

# 架构设计质量评估

只回答：模块是否值得重构、阻塞点是什么、先改哪里。以复杂度管理、职责与内聚、耦合、信息隐藏、抽象一致性和变化隔离为主轴；不做语法检查、语言技巧点评、lint、全仓巡检或完整重构设计。

执行优先级固定为：**功能准确可用性 > Context 节省 > 速度 > Token 节省**。不得为提速或省上下文跳过设计轴、截断事实或伪装覆盖。

## 范围门

在用户确认路径、语言、范围文件、是否喂入项目规约和一句话职责前，只枚举文件与粗结构。首条请求已给齐并声明确认时直接通过。读取 [scope-and-boundary.md](references/scope-and-boundary.md) 完成此门。

## 工作流

### 1. 生成完整事实索引

范围确认后读取 [analysis-protocol.md](references/analysis-protocol.md)，并只读取当前语言的 [evidence-jvm.md](references/evidence-jvm.md) 或 [evidence-cpp.md](references/evidence-cpp.md)。运行：

```bash
python3 <skill-dir>/scripts/scan_architecture.py <module-path> \
  --root <repo-root> --output <temporary-scan.json>
```

完整依赖事实只留在磁盘。使用 `query_scan.py --hotspots|--cycles|--type <name>|--file <path>` 按需读取子图；禁止把完整索引直接塞进模型上下文。扫描命中只作线索，必须读必要源码确认架构角色。

C++ 优先用 compile database + Clang AST 提取依赖；不可用时显式降级。工具失败只影响覆盖与 confidence，不产生语法类 finding。

### 2. 并行两个架构轨

读取 [design-quality-rubric.md](references/design-quality-rubric.md) 和 [candidate-contract.md](references/candidate-contract.md)。共享已确认范围与扫描索引，并行执行：

- **轨 A：结构设计** —— 复杂度管理、职责与内聚、信息隐藏、抽象层级一致性。
- **轨 B：依赖与演进** —— 耦合与依赖方向、变化隔离；仅在 `conventions_fed=true` 时读取 [convention-checking.md](references/convention-checking.md)。

可用并行 Agent 时各分派一个轨；否则顺序执行但复用同一索引。子 Agent 只返回候选 JSON，不写最终文件、不定 verdict、不返回长篇过程。主分析者综合六轴得出架构可理解性。

### 3. 合并并诚实声明覆盖

读取 [severity-and-priority.md](references/severity-and-priority.md)。主分析者：

1. 合并同源证据；通用原则与项目规约重叠时只保留一条结构 finding。
2. 分开填写 `severity` 与 `confidence`。
3. 把范围、索引、精读和语义解析文件分别写入 `coverage`。
4. 六轴逐项写 `concern`、`no-material-concern` 或 `inconclusive`。
5. 按 confirmed critical、覆盖充分性计算 `no-go`、`go` 或 `inconclusive`。

仅在存在 critical、probable/hypothesis 或 P1 先决冲突时做第二遍建议性裁判；裁判不得新增事实。

### 4. 写唯一事实源并校验

读取 [findings-json-schema.md](references/findings-json-schema.md)，只由主分析者写：

`docs/arch-diagnosis/YYYY-MM-DD-<module>-findings.json`

并行运行：

```bash
python3 <skill-dir>/scripts/validate_findings.py <findings.json>
python3 <skill-dir>/scripts/validate_evidence.py <findings.json> --root <repo-root>
```

任一失败先修 JSON 或证据。随后确定性渲染并并行验收：

```bash
python3 <skill-dir>/scripts/render_report.py <findings.json> --output <report.md>
python3 <skill-dir>/scripts/validate_report.py <report.md>
python3 <skill-dir>/scripts/validate_contract.py <findings.json> <report.md>
```

只有 renderer 排错时读取 [report-template.md](references/report-template.md)。四门全过后才交付，并说明这是重构前诊断。

## 质量纪律

- finding 必须由真实 `file:line`、职责事实或依赖边支撑，证据位于 `coverage.scope_files`。
- 大小、扇出、目录名、命名空间和 Git 共变更只用于定位候选，不单独构成 finding。
- 不从代码现状推断项目规约；规约只接受用户手工输入。
- 不把语言语法、模板、指针、所有权、格式或编译错误列为架构问题。
- 不额外运行 javac、Gradle、Maven 或完整构建来评价语法/功能正确性；若语义取证工具因编译状态不可用，只登记 coverage gap。Clang 仅作为 C++ 依赖取证 backend，不报告编译质量。
- `go` 只适用于覆盖充分且没有 confirmed critical；覆盖不足必须 `inconclusive`。
- 改进只写方向，不写目标架构和完整迁移步骤。

## 资源路由

| 阶段 | 必须读取 | 条件读取 |
|---|---|---|
| 范围 | `scope-and-boundary.md` | — |
| 取证 | `analysis-protocol.md` | `evidence-jvm.md` 或 `evidence-cpp.md` 二选一 |
| 两轨 | `design-quality-rubric.md`、`candidate-contract.md` | `convention-checking.md`（仅喂入规约） |
| 合并 | `severity-and-priority.md` | — |
| JSON | `findings-json-schema.md` | — |
| 报告 | 直接运行 renderer | `report-template.md`（仅排错） |

普通诊断不要读取脚本源码或完整示例。路径按本文件所在目录解析，不假设工作目录固定。
