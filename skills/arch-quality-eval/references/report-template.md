# report.md 渲染契约

报告必须由 `render_report.py` 从 v2 findings 生成，禁止手写第二份事实源。

固定内容：

1. frontmatter：schema、模块、语言、scope_files、覆盖计数、充分性、规约标志、三态 verdict、严重度计数和 confirmed critical 数。
2. 范围与覆盖：区分范围、索引、精读和语义解析。
3. 诊断结论：go / no-go / inconclusive 及依据。
4. 六轴设计原则矩阵。
5. 项目规约表（仅喂入时）。
6. 每个唯一结构 finding 的证据、原则、规约、confidence、影响、分级和优先级。
7. 架构可理解性、优先级和已知缺口。

renderer 或契约校验失败时修 JSON；只有确定是格式生成缺陷时才修改 renderer。
