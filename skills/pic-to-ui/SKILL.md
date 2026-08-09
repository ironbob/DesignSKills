---
name: pic-to-ui
description: "Trigger only when the user explicitly asks to use this skill by name: `$pic-to-ui`, `pic-to-ui`, or a namespaced form ending in `:pic-to-ui`. Do not trigger from task similarity, screenshot, UI, restore, or repair keywords, or inferred intent. Reconstructs native App UI from reference screenshots, or audits and repairs an existing native UI that does not visually match. Any code creation or modification requires the user to also explicitly invoke `$arch-first-code-gen`, which owns architecture confirmation and coding while pic-to-ui owns the visual contract and acceptance."
---

# 截图还原与修复 UI

## 目标与模式

把一张或多张原生 App 截图作为**目标视觉契约**，选择一种模式完成单屏 UI：

- `create`：目标屏尚未实现；从截图创建视图文件。
- `repair`：目标屏已有实现，但渲染效果与截图不一致；先审计现状，再最小化修改现有代码并验证差异是否关闭。

两种模式都防止四类偷懒：布局不一致、功能入口缺失、图标被文字/emoji 代替、尺寸比例失真。`repair` 模式额外防止直接重写、破坏现有行为，以及只说“已修复”却没有前后证据。

**编码必须使用 `$arch-first-code-gen`**：本 skill 负责定义“视觉上应该是什么”和验证“最终是否对齐”；`arch-first-code-gen` 负责确认角色/职责/依赖、生成或修改代码、产出设计契约与架构文档。不得由 pic-to-ui 绕过架构门直接编码。

只处理**一屏及其截图可见交互态**。不画设计稿、不扩展产品需求、不创建完整工程脚手架、不擅自重构无关代码。

```text
create: 截图 ─► blueprint ─► arch-first-code-gen ─► 代码/素材对账 ─► acceptance + report
repair: 截图 + 现有实现 ─► blueprint + repair-audit ─► arch-first-code-gen ─► 定点修复 ─► 验收闭环
```

<HARD-GATE>
在 `blueprint.json` 通过 Gate 1、`delivery.json + assets-manifest.json + 真实代码` 通过 Gate 2，且
`acceptance.json + report.md` 通过 Gate 3 前，不交付。

任何代码创建或修改前，必须完整执行用户已显式点名的 `$arch-first-code-gen`。架构角色确认完成前不编码；交付时 `delivery.meta.architecture_guard` 必须记录其 design-contract、架构文档、验证证据和调用方式。若当前请求没有显式点名 `$arch-first-code-gen`，停在视觉蓝图/差异审计阶段，请用户补充调用，不得静默加载或自行模拟该 skill。

`repair` 模式还必须在编辑前后分别运行 `validate_repair.py --phase audit|closure`，两次都必须传
`--blueprint` 与真实 `--code-root`。闭环时每项差异必须 `resolved`（真实锚点 + matched 证据）或
`flagged`（reason/impact/next_action）；不得保持 `open` 或把 improved 冒充 resolved。

视觉 diff 和语义自检仍是顾问式证据：能渲染就执行；不能渲染就在 `report.md` 和 `repair-audit.json` 中明确说明，不声称视觉已匹配。
</HARD-GATE>

## 输入确认与模式选择

1. 接收目标截图、可选文字标注和目标工程。
2. 确认请求同时显式点名 `$pic-to-ui` 与 `$arch-first-code-gen`。缺少后者时可以完成只读截图解析和现状审计，但不得创建或修改代码。
3. 确认平台、实际 UI 框架、目标屏入口/文件与模式：已有实现即选 `repair`，没有实现即选 `create`。同时确认该栈已被 `$arch-first-code-gen` 的标准做法库支持；不支持时停在只读蓝图/审计阶段，不得假装完成架构门。
4. 一句话重述“要对齐哪一屏、平台/框架、模式、范围=单屏含可见交互态”。仅在框架或目标屏无法从工程确定时询问用户。
5. 在 `blueprint.meta.mode` 写入 `create | repair`；其余字段遵循 `references/blueprint-schema.md`。

## 共同工作流

1. 加载 `references/restoration-workflow.md`，按结构骨架 → 功能入口 → 图标 → 关键尺寸 → 交互态 → 位图解析截图，生成 `blueprint.json`。每条视觉目标带 `screenshot_anchor`；入口宁可多标，不可漏。
2. 运行 Gate 1。空的 entries/icons/key_dimensions/states 必须在 `empty_reasons` 中逐类解释；裸空数组失败：

   ```bash
   python3 <skill-dir>/scripts/validate_blueprint.py <blueprint.json>
   ```

   失败就补蓝图；通过后才创建或修改代码。
3. 加载 `references/architecture-handoff.md`，把通过 Gate 1 的视觉契约交给 `$arch-first-code-gen`。由它完成架构确认、设计契约、编码和架构自检；pic-to-ui 不并行编辑代码。加载 `references/blueprint-schema.md` 和 `references/icon-sourcing.md`，在编码过程中同步填写 `delivery.json` 与 `assets-manifest.json`。
4. 运行 Gate 2：

   ```bash
   python3 <skill-dir>/scripts/validate_delivery.py <blueprint.json> <delivery.json> <assets-manifest.json> <code-root>
   ```

   P0 entry/icon/structure 必须真实交付，`flagged` 会阻断。只有用户明确批准时才可写
   `waived + waiver.approved_by=user + evidence`。Gate 2 会检查真实文件、widget/symbol、图标
   code_reference、素材文件、许可和 manifest 对账；失败就修实现或取得明确豁免。
5. 重新渲染目标屏并与参考截图并排比较；优先在相同设备尺寸、缩放、主题、动态字体、语言和系统栏配置下截图。无法控制的环境差异要标明。
6. 生成 `acceptance.json` 与 `report.md`：前者按 `references/acceptance-schema.md` 记录门禁、diff、
   七维自检、测试和 flags，后者给人阅读。运行 Gate 3：

   ```bash
   python3 <skill-dir>/scripts/validate_acceptance.py <acceptance.json> <delivery.json> <artifact-root> [--repair-audit <repair-audit.json>]
   ```

   Gate 3 失败不得交付。diff 不可用可以写 `unavailable + reason + unverified`，但不能伪装 matched。

## repair 模式专用工作流

执行共同工作流第 1–2 步后，加载 `references/repair-workflow.md` 和 `references/repair-schema.md`，再按以下顺序进行：

1. **保护现有行为**：先读目标屏、组件、主题/token、资源和相关测试。记录当前交互、状态、导航及数据绑定；不要为视觉对齐破坏它们。检查工作树并保留用户已有改动。
2. **建立基线**：尽可能运行现有预览、模拟器或截图测试，保存当前渲染；无法渲染时记录原因，并用代码检查 + 用户提供的当前效果作为降级证据。
3. **逐项差异审计**：把目标截图与当前渲染/实现按 `structure | entry | icon | dimension | style | state | bitmap` 比较。生成 `repair-audit.json`，每个 mismatch 关联一个或多个 blueprint id、截图证据、当前证据、诊断和当前代码锚点。
4. **运行修复审计门**：

   ```bash
   python3 <skill-dir>/scripts/validate_repair.py <repair-audit.json> --phase audit --blueprint <blueprint.json> --code-root <root>
   ```

   通过前不修改 UI；审计项必须是可追溯、可行动的真实差异，不为通过门禁虚构 mismatch。
5. **交给架构编码阶段**：把 blueprint、repair-audit、目标文件、必须保留的行为和当前架构证据交给 `$arch-first-code-gen`。由它按根因小步修改并完成设计契约；pic-to-ui 不自行追加“最后一点视觉补丁”。
6. **每轮重新渲染**：pic-to-ui 对照原截图复查；已改善但仍未对齐的项保持 `open`，把剩余 mismatch 反馈给同一代码所有者继续迭代。没有新截图时不得把仅靠静态代码判断的视觉项写成 `matched`。
7. **关闭差异**：在 `repair-audit.json` 中把每项置为：
   - `resolved`：含 `resolution.code_anchor`、改动摘要，以及 `verification.method/result/evidence`；`result` 只能是 `matched`。
   - `flagged`：含无法安全关闭的原因、影响和建议后续动作。
8. **运行修复闭环门**：

   ```bash
   python3 <skill-dir>/scripts/validate_repair.py <repair-audit.json> --phase closure --blueprint <blueprint.json> --code-root <root>
   ```

   失败就继续修复或标红；不得以“代码已改”代替视觉验证。
9. 完成共同工作流第 3–6 步。`delivery.json` 的 `code_anchor` 指向最终现有文件；`report.md` 汇总修复前后证据、未解决项和回归测试。

## 优先级与修复顺序

- P0：结构、控件/功能入口、图标不得降级为文字。先修。
- P1：尺寸、间距、字体、颜色、状态。随后修。
- P2：图标图案精度和轻微装饰差异。语义正确优先，仍要如实记录。

若一个上游问题造成多处视觉偏差（例如父容器宽度导致文本换行和按钮错位），先修上游约束，再重新审计下游项，避免用多组 magic number 掩盖根因。

## 交付物

存到用户指定位置；未指定时用 `pic-to-ui/YYYY-MM-DD-<主题>/`：

- `blueprint.json`：截图定义的目标契约。
- `delivery.json`：目标条目到最终代码锚点的交付对账。
- `assets-manifest.json`：图标/位图来源与许可。
- `acceptance.json`：Gate、diff、自检、测试与 flags 的机器验收事实源。
- 视图代码：create 模式为新文件；repair 模式为现有文件的最小必要修改。
- `report.md`：门禁、自检、diff、测试、标红与未决问题。
- `repair-audit.json`：仅 repair 模式；差异、根因、修改锚点和前后验证证据。
- 可选 `evidence/`：仅在实际生成时保存 baseline、after、overlay 或 diff 图；不要伪造证据文件。

脚本路径必须从本 `SKILL.md` 所在目录解析，不要假设当前目录是仓库根。作为插件加载时可使用 `${CLAUDE_PLUGIN_ROOT}/skills/pic-to-ui/scripts/`。

## 自审

1. 确认选择了正确模式；repair 没有悄悄变成整屏重写。
2. 确认 `$arch-first-code-gen` 已完成角色确认、设计契约、架构文档和原则复核；pic-to-ui 没有绕过它直接改代码。
3. 重跑适用的所有 Gate，确认 exit 0；Gate 2 必须传真实 code-root，Gate 3 必须传交付目录。
4. 抽查截图里的每个入口、图标和结构节点都真实 delivered；P0 不得以 flagged 绿灯。
5. 确认 delivered 图标使用真实资源，未用文字、emoji 或占位符替代。
6. repair 模式确认每个 mismatch 已 resolved 或 flagged，resolved 有代码锚点和真实验证证据。
7. 确认修改未破坏已有交互、状态、导航、数据绑定和相关测试；记录未能运行的测试。
8. 确认 report 没把静态检查写成视觉匹配，也没把 `improved` 写成完全 `matched`。
9. 确认所有不确定项、环境差异、未执行 diff 和用户需确认事项均已标红。
10. 运行 `python3 -m unittest discover -s <skill-dir>/tests -v`，确认 validator 回归测试通过。

## 边界与反模式

| 反模式 | 正确做法 |
|---|---|
| 看到截图就直接写/重写代码 | 先生成目标 blueprint；repair 再做现状审计 |
| pic-to-ui 自己绕过架构门写代码 | 显式调用 `$arch-first-code-gen`，由它拥有代码修改 |
| pic-to-ui 与架构编码代理同时改同一文件 | 串行交接；视觉代理验收，代码代理修改 |
| 只列差异，不实际修复 | 定位根因、修改现有文件、重渲染并关闭 mismatch |
| repair 时抛弃现有组件和业务逻辑 | 复用结构，做最小必要修改，回归行为 |
| 用一堆局部偏移掩盖父布局问题 | 先修上游约束，再复查下游差异 |
| 没有 after 渲染就声称视觉 matched | 将该项标为 `flagged`，并说明渲染为何不可用 |
| 省略“小”入口或布局节点 | P0 必须真实 delivered；用户明确 waiver 除外 |
| 图标用文字/emoji 顶替 | 下载、系统图标资源或自绘，并登记许可 |
| 把截图里的固定像素机械套到所有设备 | 在基准设备对齐，保留工程既有响应式约束 |
| 修改无关代码或顺手重构 | 限定到差异根因相关文件，报告实际改动范围 |

超出范围的多屏跳转、产品逻辑新增、完整脚手架、动画和完整 a11y 审计，写入 `report.md` 未决问题，不擅自扩展。

## 参考资源

- `references/blueprint-schema.md`：blueprint、delivery、assets 契约。
- `references/restoration-workflow.md`：共同解析与实现流程。
- `references/repair-schema.md`：repair-audit 契约。
- `references/repair-workflow.md`：现有实现审计、根因修复与回归方法。
- `references/architecture-handoff.md`：与 `$arch-first-code-gen` 的交接、代码所有权和子代理选择。
- `references/acceptance-schema.md`：Gate 3 的结构化验收契约。
- `references/validation-rules.md`：全部硬门与视觉判断边界。
- `references/icon-sourcing.md`：图标来源、许可与位图处理。
- `scripts/validate_blueprint.py`：Gate 1。
- `scripts/validate_delivery.py`：Gate 2。
- `scripts/validate_repair.py`：repair 审计门与闭环门。
- `scripts/validate_acceptance.py`：Gate 3，验证 report、diff、自检、测试与 flags。
