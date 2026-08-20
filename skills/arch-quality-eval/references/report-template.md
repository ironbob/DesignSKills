# report.md 渲染契约

普通诊断不要读取本文件，也不要让模型手写报告。运行：

```bash
python3 <skill-dir>/scripts/render_report.py <findings.json> --output <report.md>
```

仅在修改 `render_report.py` 或排查报告校验失败时使用本契约。

## Frontmatter

必须从 JSON 同步：

- `module`、`title`、`language`、`analyzed_at`
- `covered_files`
- `conventions_fed`
- `no_go_threshold`、`verdict`
- `critical_count`、`major_count`、`minor_count`
- `cpp_limitation_noted`
- `open_questions`：`unconfirmed=true` 的 finding 数
- `status: draft`

## 正文章节

1. **评估范围**：路径、覆盖文件数、语言/结构、职责基线、规约状态。
2. **go/no-go 门禁结论**：verdict、critical 数/阈值、全部 critical 项。
3. **架构坏味道清单**：核心五类覆盖矩阵 + smell finding 块。
4. **项目规约违规**：仅 `conventions_fed=true` 时生成。
5. **架构可读性**：四轴、总体结论、readability finding 块。
6. **重构优先级总览**：P1/P2/P3 与排序依据。
7. **评估方法与已知缺口**：符号模式、聚焦、Git、omissions、known_gaps、边界。

没有规约时后续章节编号自动前移。没有 finding 时仍生成核心覆盖矩阵、四轴和 go verdict。

## finding 块

每个 JSON finding 必须且只能有一个四级标题块：

```markdown
#### FINDING-S01 · 标题 · 🔴 critical

- 证据：`src/Foo.java:42`（note）
- 违反原理：单向依赖原则
- 影响：……
- 分级依据：……
- 改进方向：……
- 修复成本：high　优先级：P1（……）
```

convention finding 把“违反原理”替换为“违反规约”。每个块至少带一个源码文件锚点；不再要求报告全局凑够三个不同锚点。

## 渲染纪律

- 只从 JSON 渲染，不新增、删减或改写事实。
- JSON 中每个 finding id 必须有详细块；仅在优先级表提到不算完成渲染。
- 正文 severity 必须与 JSON 一致，三个计数都要对账。
- 不输出完整重构方案、lint、CI 门禁或自动推断的项目规约。
- 修改 renderer 后依次运行 `validate_report.py` 和 `validate_contract.py`。
