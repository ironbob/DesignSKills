# 门禁规则：文本图确认门 + 编码路径门 + 三道交付门 + repair 两阶段门

只把确定性规则设为 ERROR、卡 exit code。视觉相似度和语义判断依赖真实渲染、diff 与逐项自检；它们写入 `report.md`，不能伪装成脚本已验证。

## 一、验收层次

| 验收 | 适用模式 | 是否卡 exit | 解决什么 |
|---|---|---|---|
| Gate 0 draft/confirmed `validate_text_ui.py` | create / repair | 是 | 每张截图有独立文本 UI 图，且后续流程前已获用户逐图确认 |
| Gate 1 `validate_blueprint.py` | create / repair | 是 | 截图目标契约完整、字段齐全、无偷懒占位 |
| Repair audit `validate_repair.py --phase audit --blueprint ...` | repair | 是 | 编辑前有基线、差异证据、根因和当前代码落点 |
| Coding Path `validate_change_assessment.py` | create / repair | 是 | 编码前决定 direct_ui 或 arch_first；实际范围扩大时重跑 |
| Gate 2 `validate_delivery.py` | create / repair | 是 | P0 真实交付、代码锚点存在、图标/位图与素材清单对账 |
| Repair closure `validate_repair.py --phase closure --blueprint ...` | repair | 是 | 每项差异 matched+真实锚点，或 flagged+原因/影响/后续 |
| Gate 3 `validate_acceptance.py` | create / repair | 是 | report、diff 状态、七维自检、比例台账、测试和标红清单完整 |

## 二、Gate 0：逐截图文本 UI 图确认（`TXT.*`）

| 规则码 | 级别 | 判定 |
|---|---|---|
| `TXT.meta/screenshots/count` | ERROR | manifest 有屏幕名；source_count、text_ui_count 与截图条目数一致 |
| `TXT.item/one_to_one` | ERROR | 每张截图有唯一 SHOT id、source 和独立 text_ui_file，不能共用文件 |
| `TXT.file.*` | ERROR | `.txt/.md` 文件在 artifact-root 内真实存在，且含足够文本绘图结构而非 prose |
| `TXT.confirmation.draft` | ERROR | rejected 项必须修订并重置 pending 后才能展示 |
| `TXT.confirmation.user` | ERROR | confirmed phase 每项均为 user_confirmed、confirmed_by=user 且有真实 evidence |

draft 通过后必须展示全部文本图并结束当前轮次。confirmed 未通过前不得生成 blueprint、repair audit、架构或代码；自动确认不适用。

## 三、Gate 1：蓝图完整性（`BP.*`）

| 规则码 | 级别 | 判定 |
|---|---|---|
| `BP.meta` | ERROR | mode/platform/framework/screen_job/scope/source_screenshots 完整 |
| `BP.text_ui.parity` | ERROR | blueprint 截图顺序/id 与 confirmed text-ui manifest 一致 |
| `BP.category.<cat>` | ERROR | structure_skeleton/entries/icons/key_dimensions/states 键齐全 |
| `BP.structure.nonempty` | ERROR | structure_skeleton 是含 `node_id` 的非空根节点 |
| `BP.structure.fields/unique/children` | ERROR | 每个结构节点含 node_id/kind、id 唯一、children 为数组 |
| `BP.entry.fields/unique` | ERROR | 每条 entry 含 id/kind/semantic/screenshot_anchor，id 唯一 |
| `BP.icon.fields/unique` | ERROR | 每条 icon 含 id/semantic/screenshot_anchor，id 唯一 |
| `BP.<category>.count` | ERROR | entries/icons/key_dimensions/states 非空，或有结构化 empty_reasons.<category> |
| `BP.empty_reasons.*` | ERROR | 空类别原因是合法 key 下的非空文字 |
| `BP.dimension.fields/unique` | ERROR | 每条尺寸含 id/what/ratio_note，id 唯一 |
| `BP.state.source` | ERROR | state.source 为 screenshot 或 inferred |
| `BP.state.unique` | ERROR | state id 非空且唯一 |
| `BP.placeholder` | ERROR | 全文无 TODO/TBD/FIXME/待定/待补/lorem |

## 四、编码路径门（`CPA.*`）

- direct_ui：无 risk flag，逻辑为 none/local_wiring，且 small 或 ui_only；
- arch_first：业务逻辑、导航、状态所有权、数据流、API/存储、依赖、跨层职责、共享影响、
  多屏或架构角色任一命中；
- production_files 与 small/medium/large 档位必须一致；
- 实施中范围扩大时递增 revision 并重跑，不能继续使用旧结论。

## 五、Gate 2：交付对账（`DLV.*`）

每个 blueprint 条目必须：

- `delivered`：带 `code_anchor{file, widget}`；或
- `flagged`：仅 P1 可以带 `reason` 后通过结构门；P0 flagged 阻断；或
- `waived`：仅 P0，且必须有用户明确批准的 waiver evidence。

Gate 2 必须传入 `assets-manifest.json`、`change-assessment.json` 和真实 `code-root`。所有 delivered 锚点的文件和
widget/symbol 都必须能在 code-root 内真实定位。

| 规则码 | 级别 | 判定 |
|---|---|---|
| `DLV.entry` | ERROR（P0） | 每个入口 delivered；flagged 阻断，只有 user-approved waived 可例外 |
| `DLV.icon.not_text` | ERROR（P0） | delivered 图标 asset.type 为 downloaded/self_drawn，绝不允许 text/emoji/placeholder |
| `DLV.icon.anchor` | ERROR（P0） | delivered 图标带 code_anchor |
| `DLV.icon` | ERROR（P0） | 每个图标 delivered 或显式 user waiver |
| `DLV.structure` | ERROR（P0） | 每个结构节点 delivered 或显式 user waiver |
| `DLV.dimension/state` | ERROR（结构） | 每个尺寸/状态必须 delivered，或完整 flagged；视觉正确性仍为 P1 |
| `DLV.*.file/widget` | ERROR | delivered 锚点文件真实存在且含声明 symbol |
| `DLV.icon.code_reference` | ERROR | 锚点代码真实引用声明的图标资源 |
| `DLV.dangling` | ERROR | delivery 不引用 blueprint 外的 id |
| `DLV.unique` | ERROR | delivery 各类别 id 不重复 |
| `DLV.present` | ERROR | delivery 顶层是对象 |
| `CPA.*` | ERROR | assessment 的规模、风险和 direct_ui/arch_first 决策一致 |
| `DLV.coding_path` | ERROR | delivery 路径、assessment revision 和代码所有者一致 |
| `DLV.change_scope*` | ERROR | 实际生产文件数量、revision 和 code anchors 与 assessment 一致 |
| `DLV.architecture.file` | ERROR | 仅 arch_first：设计契约与架构文档真实存在且不越出 code-root |
| `AST.*` | ERROR | 素材 id/语义/类型/来源/许可/文件与 blueprint、delivery 一致 |
| `AST.icon.source_policy` | ERROR | 图标有指定网站检索轨迹；自绘 SVG 前 Iconfont、Lucide、Material Symbols 三站均记录 not_found |

P0 包含结构、功能入口和图标不降级；P1 包含尺寸、状态和主要样式；P2 包含轻微装饰和图标图案精度。P1/P2 的视觉正确性由 diff 和自检判断。

direct_ui 不要求架构文档；arch_first 必须完整执行对应 skill。两条路径都不能在编码后倒填一个
与实际范围不符的 assessment。

## 六、Repair 两阶段门（`RPR.*`）

`--phase audit` 在修改前检查（`--code-root` 必填）：

- `meta.mode = repair`；
- baseline 为 captured/provided + evidence，或 unavailable + reason；
- mismatches 非空；
- 每项有唯一 id、类别、优先级、关联 blueprint id、目标/现状证据、诊断；
- 每个 target id 确实存在于传入的 blueprint（全局环境差异可用 `META`）；
- 每项有当前代码锚点或找不到落点的原因；声明锚点必须真实存在；
- 每项 status 为 `open`。

`--phase closure` 在修改后检查：

- 不得残留 `open`；
- `resolved` 有改动摘要、真实代码锚点和 `matched` 验证证据；
- `flagged` 有 reason/impact/next_action；
- 纯视觉类别不能以 `static_inspection + matched` 关闭。

Repair gate 只验证差异声明和证据结构，不自动判断截图是否真的相似。若 after 无法渲染，纯视觉差异应 flagged 为未验证，而不是伪造 matched。

## 七、Gate 3：结构化验收

重新截图 diff 和 AI 自检的视觉结论仍需模型判断，但是否执行、证据是否存在、覆盖是否完整，
以及 delivery/repair flagged/waived 是否原样汇总，由 Gate 3 硬卡。契约见 `acceptance-schema.md`。

### 重新截图 diff

能渲染时，在尽量一致的设备、缩放、主题、字体、语言、系统栏和 fixture 下生成 after 截图，与参考图和 before 并排比较；可选生成 overlay/diff。把残差关联到 blueprint/mismatch id。

不能渲染时，在 `acceptance.json` 写 `unavailable + reason + unverified`，并同步到 report；
不能声称纯视觉已匹配。

### AI 逐项自检

强制覆盖 structure/entries/dimensions/style/icons/states/a11y 七维。每项给判定与证据；
P0 存疑阻断，P1/P2 存疑进入 flags。另须逐 `DIM-##` 建立比例验收台账：在同一基准环境测量参考/after 的分子与分母，脚本复算偏差；通过项须在容差内，未通过或未验证项必须进 flags。

## 八、结构性与语义性边界

| 能力 | 谁查 | 强度 |
|---|---|---|
| 截图与文本图一一对应、文件存在、用户确认字段 | Gate 0 | 结构性硬门 |
| 蓝图类别/字段/占位符 | Gate 1 | 结构性硬门 |
| 改动量、逻辑/架构风险和编码路径 | Coding Path Gate | 结构性硬门 |
| 条目交付或标红、图标资源类型 | Gate 2 | 结构性硬门 |
| repair 差异有根因、关闭状态和证据 | Repair gates | 结构性硬门 |
| 声明的文件是否存在 | Gate 2/Repair parity | 结构性证据 |
| diff、自检、测试、flags 是否完整且有真实文件 | Gate 3 | 结构性硬门 |
| 布局、尺寸、颜色、字体、图标是否真的视觉一致 | 真实渲染 + diff + 自检 | 语义性判断 |

## 九、双端阶段门

双端适配仍一次一端：基准端先通过适用的全部门禁并由用户确认效果，再开始适配端。适配端沿用 entry/icon/structure id 体系并重新跑全部适用门禁。repair 模式下每一端各有独立 repair-audit。

## 十、ERROR 处理

- `TXT.*`：补齐逐图文件/绘图结构；展示给用户并取得明确确认，不能自行代签。
- `BP.*`：回截图目标解析，补类别、字段、来源或移除占位符。
- `CPA.*`：补真实文件/风险证据并纠正编码路径；若升级 arch_first，停止直接编码。
- `DLV.entry`/`DLV.structure`：真实现并登记 code_anchor，或诚实 flagged。
- `DLV.icon.not_text`：换成从指定站点下载的 SVG，或在三个站点均无匹配证据后自绘 SVG。
- `RPR.audit.*`：编辑前补基线、差异证据、根因或当前落点。
- `RPR.closure`/`RPR.verification`：继续修复并重新渲染，或 flagged；不能用静态检查冒充视觉 matched。

修完重跑所有适用门禁；最终把门禁结果、diff、自检、测试和 flagged 项写入 `report.md`。
