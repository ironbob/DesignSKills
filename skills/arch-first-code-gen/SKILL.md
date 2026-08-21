---
name: arch-first-code-gen
description: "Trigger only when the user explicitly asks to use this skill by name: `$arch-first-code-gen`, `arch-first-code-gen`, or a namespaced form ending in `:arch-first-code-gen`. Do not trigger from task similarity, coding or architecture keywords, repository contents, or inferred intent. For one new requirement across JVM, C++, FastAPI+Vue, or Swift/iOS, selects a user-approved risk-sized design profile, aligns with the repository, compares decompositions, confirms role/interface/invariant/verification contracts, and waits for explicit design approval before implementing responsibility-split code and verified architecture artifacts. May parallelize read-only discovery and design review with subagents when speed matters, but the primary agent alone writes all production code, test code, configuration, contracts, and delivery documents. For UI code, assesses the existing architecture first and avoids mechanical MVVM adoption."
---

# 架构先行代码生成

针对一个已经明确的新 feature，先确认风险等级和架构，再编码、验证并交付职责清晰的代码与架构证据。本 skill 不澄清产品需求、不评估或重构已有模块，也不处理全仓重构、DB 迁移、性能算法选型、UI 视觉细节、lint 或 CI 门禁。

执行优先级固定为：**功能准确可用性 > context 节省 > 速度 > Token 节省**。以《代码大全2》的复杂度管理、信息隐藏和构造质量为主指导；SOLID、DDD、分层架构及仓库惯例仅作次级工具，不得为了模式完整牺牲正确性或简洁性。

## 不可绕过的确认门

在任何生产代码、测试、配置或交付文档写入前，严格执行：

1. **等级选择门**：只读勘察仓库，推荐 `light / standard / high_risk`，等待用户明确选择。用户初始请求已明确 profile 时本门完成；“你决定”“直接做”不算选择。
2. **方案确认门**：展示当前版本的完整方案后结束回合。只有后续用户消息明确确认当前候选和方案版本，才可写仓库。初始请求不能预先确认尚未展示的方案。

方案必须先展示：profile 与质量属性、候选与取舍、角色职责/依赖/隐藏秘密/变化触发器/数据所有权、关键接口的输入输出/前后置条件/不变量/错误/事务并发边界、业务流程和验证策略。方案实质变化时递增 revision，旧确认失效并重新确认。

UI feature 还要确认当前/目标模式、状态所有者和 MVVM 适用性。新引入 MVVM 且迁移影响为 `high` 时，必须取得独立的用户迁移确认；通用方案确认不能替代。`high_risk` 在生产编码前必须完成 spike，并由用户或同行复核结论。

确认前只允许只读检查和对话分析；不得创建 contract 草稿、调用编辑工具或伪造确认凭据。

## Profile

| Profile | 使用条件 | 编码前最小内容 |
|---|---|---|
| `light` | 局部、低风险、沿用成熟模式、无公共语义变化 | 1 个候选、1–2 个关键质量属性、最少角色和跨角色接口、验证命令 |
| `standard` | 跨多个角色、有业务流程或公共边界 | 至少 2 个候选、完整角色/接口/流程、独立复核 |
| `high_risk` | 资金、权限、不可逆数据、复杂并发事务、跨上下文或技术不确定 | `standard` + spike + 用户/同行评审 |

以风险而非代码行数推荐等级。`light` 默认控制在 3 个主要角色内；超过时必须说明每个额外角色隐藏的独立变化秘密。没有真实领域不变量时不要为了 DDD 创建聚合或领域服务。

## 速度优先的多 Agent 策略

当运行环境支持子 agent 且 `standard/high_risk` 存在两个以上独立分析面时，允许并行执行**只读工作**：`standard` 最多 2 个，`high_risk` 最多 3 个，即使总 Token 增加：

- 仓库勘察：分别检查架构/依赖、构建/测试、日志/UI 状态边界。
- 方案阶段：分别提出候选分解或做独立复核，主 agent 统一裁决并展示一个完整方案。
- 编码完成后：只读复核职责、依赖、测试覆盖和契约漂移；只返回发现，不修改文件。

**编码不得拆给子 agent。** 主 agent 独占所有写操作，包括生产代码、测试代码、配置、构建文件、`design-contract.json`、架构文档和修复。子 agent 不得调用编辑工具、生成补丁或在共享工作区创建交付文件。测试与校验由主 agent 运行；可在一个工具调用中并行执行互不冲突的命令。

只向子 agent 提供当前子任务所需的目录、约束和问题，不传完整对话或全部 references。要求返回不超过 500–700 Token 的结构化结论：`facts / risks / recommendation / evidence_paths`；主 agent 只合并证据，不转录推理过程。

`light` 默认单 agent；只读勘察明显跨多个独立模块时才启用子 agent。没有可并行分析面时不要为并行而并行。

## 分阶段执行与加载

不要预加载全部 references，也不要读取其他栈文件。相同任务已读过的材料不要重复读取。

### A. 只读对齐与等级选择

仅读 [scope-and-alignment.md](references/scope-and-alignment.md)。用 `rg`，不可用时用 `find`，粗读相关目录并限制命令输出；识别 feature 边界、技术栈、现有分层/命名/日志/依赖注入/测试习惯。需要时按上面的只读策略并行勘察。说明三个 profile 的成本与推荐，然后等待用户选择。

若用户初始消息已经明确 profile，直接进入 B；这是省去等级选择回合的正式快路径，不等于预先确认方案。

### B. 编码前方案

读取：

- [architecture-design-method.md](references/architecture-design-method.md)
- [code-complete-design.md](references/code-complete-design.md)
- [design-principles.md](references/design-principles.md)
- [role-confirmation.md](references/role-confirmation.md)
- [business-process.md](references/business-process.md)
- 当前栈文件：[JVM](references/standard-practices/jvm.md)、[C++](references/standard-practices/cpp.md)、[FastAPI+Vue](references/standard-practices/fastapi-vue.md) 或 [Swift/iOS](references/standard-practices/swift-ios.md)
- 仅 UI：[ui-architecture-policy.md](references/ui-architecture-policy.md)

先写可判断的质量属性场景，再比较候选。可让只读子 agent 并行提出候选或独立复核，但主 agent 必须统一判断。自顶向下从流程和边界推导角色，自底向上用现有代码和框架约束反查。每个角色必须有单一职责、明确隐藏秘密、变化触发器、数据所有权、依赖、业界依据和具体设计原则。分层角色与领域角色都检查；不适用时写理由。

只冻结关键跨角色接口，不提前设计所有私有方法。完整展示当前 proposal 后询问“是否按此方案进入编码”，然后停止。

### C. 确认后编码与验证

仅在用户确认当前方案后读取 [code-complete-construction.md](references/code-complete-construction.md)、[design-contract-checklist.md](references/design-contract-checklist.md) 和 [logging-standards.md](references/logging-standards.md)，然后：

1. 运行 `scripts/init_contract.py` 生成所选 profile 的契约骨架，写入两次真实确认凭据。
2. 按角色实现代码；角色可以映射多个文件。一个文件承载多个角色时，只有职责紧密相关且记录理由才接受。
3. 用 `traceability` 将验收条件映射到角色、接口、代码、测试和命令；按 profile 补齐验证矩阵与构造复核。无法验证的项目写入 `unverified` 并降低置信度。
4. 对关键流程记录入口、结果、外部调用和异常上下文；领域对象、纯 View、DTO/Mapper/util 不为凑覆盖而打日志。
5. 由主 agent 运行 `scripts/run_verification.py <contract> --root <repo-root> --execute --update-contract`，只接受脚本写入的真实执行证据；失败不得手改为 passed。

本阶段全部代码与文件修改必须由主 agent 完成，不得把任何角色、文件、测试或修复委派给子 agent。

实现发现边界错误时回到 B，展示差异并重新确认。不要擅自引入通用测试框架或构建系统。

### D. 单源渲染与交付

`design-contract.json` 是唯一手写契约源。不要手工重复维护架构文档；运行：

```bash
python3 <skill-dir>/scripts/run_verification.py <design-contract.json> --root <repo-root> --execute --update-contract
python3 <skill-dir>/scripts/render_arch.py <design-contract.json> --output <arch.md>
python3 <skill-dir>/scripts/validate_all.py <design-contract.json> <arch.md> --root <repo-root> --summary
```

校验失败时只读取对应资料：[design-contract-schema.md](references/design-contract-schema.md)、[arch-doc-template.md](references/arch-doc-template.md) 或 [self-check-gates.md](references/self-check-gates.md)。成功时不要加载这些长文或完整成功明细。

校验结果是结构与文本证据，不替代语义复核。必须亲自判断职责是否单一、依赖是否合理、领域行为是否归位、日志是否可诊断；机器未覆盖的语义项写入 `gate.notes` 和已知缺口。

## 交付契约

存到产品仓库 `docs/architecture/` 或用户指定目录，共用 `YYYY-MM-DD-<feature>` 前缀：

- `*-design-contract.json`：机器契约源
- `*-arch.md`：由 contract 自动渲染的人读文档

交付前必须满足：

- 用户选择 profile、后续确认当前 proposal 的凭据真实且匹配 revision/candidate。
- 每个确认角色能回链真实代码；依赖可解析、无环、无明显反向层依赖。
- 流程步骤、代码引用、接口和文档能对账。
- 验收条件可追溯到角色/接口/代码/测试/机器执行命令；required 命令均由脚本执行并通过。
- 《代码大全2》构造复核无失败；不适用项有具体理由。
- `validate_all.py --summary` 通过；真实结构问题已修复，近似误伤与语义缺口已说明。

脚本位于本文件同级 `scripts/`；不要假设当前目录是仓库根。默认用当前目录作为 `--root`，必要时传绝对仓库根。脚本和 examples 不需要读入上下文，除非正在调试它们。

## 回退与边界

- 需求目标、验收或公开业务语义不明确：停止并建议先使用 `clarify-requirements`。
- 用户要求评价或重构已有模块：说明应使用 `arch-quality-eval`。
- feature 过大：拆成单 feature 或按风险热点分批。
- 用户要求跳过确认：说明本 skill 不支持，停在当前门。
- 校验 no-go：修复后重跑；不得降低阈值掩盖真实问题。

本 skill 独立完成代码、测试、契约和架构文档，不调用其他 skill。
