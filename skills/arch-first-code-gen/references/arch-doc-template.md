# 架构文档渲染指南

架构文档是 `design-contract.json` 的确定性人读渲染，不再手工双写。正常流程只运行：

```bash
python3 <skill-dir>/scripts/render_arch.py <contract.json> --output <arch.md>
```

仅在 renderer 或 `validate_doc.py` 失败时读取本文。

## 必要结构

文档由 renderer 生成以下内容：

1. frontmatter：feature、title、stack、design_profile、日期、角色/流程/缺口计数、verdict。
2. 用户确认记录：profile、proposal revision、候选和后续用户确认凭据。
3. Mermaid 模块结构图：由 `roles[].depends_on` 生成。
4. Mermaid 业务流程图：由 `business_process[]` 生成，并逐项写入 `doc_ref`。
5. 角色职责表：角色、类型、层、职责、隐藏秘密、数据所有权、依赖、原则。
6. 质量属性、候选方案、选择理由、双向检查和 spike。
7. 每角色设计依据及 UI 架构决策。
8. 关键接口的输入输出、条件、不变量、错误、数据所有权、事务和并发。
9. 实际验证命令、检查、测试引用和未验证项。

## 对账规则

- 文档角色集合必须等于 contract 角色集合。
- frontmatter 计数、profile、verdict 必须与 contract 一致。
- 每个流程 `doc_ref` 和接口 name 必须出现在文档。
- 每个角色必须在“设计依据”中点名具体原则和业界来源。
- `open_questions` 等于未决问题与 `unverified` 的合计。

不要编辑生成文档来修对账错误；修 contract 或 renderer 后重新生成。只有纯展示格式需要调整时才修改 renderer。

## 写作约束

避免空泛词和 placeholder。真实缺口写成“问题、影响、后续阶段”。辅助校验没有覆盖的 SRP、依赖合理性、日志上下文等语义判断，明确登记为语义复核或已知缺口。
