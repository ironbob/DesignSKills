# 代码托管 / 协作 / Git 平台 领域知识

> 知识复核：2026-07
> 树路径：dev-tools > code-hosting
> 继承：`dev-tools`（API / CLI 优先 / 可扩展（Webhook）/ 文档示例 / 权限安全均适用）
> 使用前先读父类：[`README.md`](README.md)

## 匹配信号
- 关键词：代码仓库 / Git 托管 / Merge Request / Pull Request / 代码评审 / Code Review / MR 合并策略 / 分支保护。
- 场景：多人协作的代码托管、PR/MR 评审与门禁、分支保护与权限治理、CI 钩子触发。

## 继承要点（速览）
开发者工具通用全适用；本类增量是——**围绕 Git 的协作契约（PR/MR 评审 + 分支保护 + CI 门禁 + Webhook）**。代码托管的本质是把"谁能改主分支、怎么改、谁批"变成可执行规则。

## 核心价值要素
让**协作变更可控、可审、可追溯**，主分支始终可信。不可缺：① PR/MR 评审与门禁（CI 通过 + 人审才能合并）② 分支保护与最小权限 ③ 事件可扩展（Webhook 触发下游）。

## 业界标配功能
- **Pull/Merge Request 流程**：源分支→目标分支、diff 评审、行内评论、@、变更审批（approve/changes requested）、merge 策略（merge commit / squash / rebase）——因为"直推主分支"是代码失控之源，PR 把每次变更变成一次可审事件。
- **分支保护与规则**：主干保护、强制评审人数、强制 CI 状态门禁、禁止 force-push、禁止删历史——保护主分支不被误推/被改写。
- **权限与组织治理**：组织/团队/仓库三级权限、最小权限（只读/写/管理员）、CODEOWNERS 自动指派评审人。
- **CI/CD 钩子集成**：PR 状态检查（status check）、必须 CI 绿才能合并——把质量门焊进合并流程。
- **Webhook / API**：push/PR/评论等事件可订阅、有 REST/GraphQL API——因为这是"平台"与"工具"的分水岭，下游（CI/通知/机器人）全靠它驱动。
- **评审辅助**：行内批注、建议（suggested change 一键提交）、轻量 issue/项目看板关联。
- **搜索与追溯**：跨仓代码搜索、blame、历史可追溯（谁在哪次提交引入的）。
- **制品/制品库/包/容器 registry 一体化**（GitLab/Azure DevOps）：仓库与流水线/制品同栈。

## 业界标杆做法
- **GitHub**：全球事实标准 — PR 流程 + Actions 一体化 + 巨大社交生态，做对了"协作 DX 与开发者网络效应"。
- **GitLab**：仓库+CI+制品+安全扫描单体 DevOps 平台 — `.gitlab-ci.yml` 同仓 + 内置 Registry/SAST，做对了"一站式减少工具拼装"。
- **Gerrit**：Change-based 评审（一个 commit 一个 review） — 做对了"逐提交精细评审 + 强制 rebase 保持线性历史"，谷歌级协作规模验证。
- **Bitbucket**：Atlassian 生态（Jira/Confluence）协同 — 做对了"与项目管理深度联动"。
- **Azure DevOps / Repos**：微软企业线 — 仓库+Boards+Pipelines+企业权限治理一体，做对了"企业级合规与 ALM 集成"。
- **Gitee**：国内代码托管 — 做对了"国内访问速度与本土合规（等保/数据本地化）"。

## 常见陷阱与反模式
- 主干无保护、可直推或 force-push → 历史被改写、误推覆盖线上，根因追溯断裂（代码托管头号失控）。
- PR 评审流于形式（无最少评审数/无 CI 门禁/无人真看）→ "评审"变橡皮图章，门禁形同虚设。
- 权限过度放开（全员管理员/长期写权限）→ 一次误操作或凭据泄露即大事故；应 CODEOWNERS 自动指派 + 最小权限。
- 重 GUI 轻 API/Webhook → 无法接 CI/机器人/自动化，被工具链绕开。
- merge 策略混乱（无约定）→ 历史满是噪音 merge commit 或被随意 squash，blame 与回滚困难。

## 本节点专属澄清
- 主干是否**分支保护**（强制评审 + CI 门禁 + 禁 force-push）？合并策略是什么（merge/squash/rebase）？
- 评审是否有**最少人数 + CODEOWNERS 自动指派**，而非橡皮图章？
- CI 状态是否是**合并硬门禁**（必须绿才能合）？
- 是否提供 **API / Webhook** 接下游（CI/通知/机器人）？
- 仓库与 **CI/制品/看板** 要不要一体化（GitLab/Azure DevOps）还是独立拼装？
- 数据是否需**本地化/等保**（影响选 Gitee/自建 vs GitHub）？公开仓库还是私有？
