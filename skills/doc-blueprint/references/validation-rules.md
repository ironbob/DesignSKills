# 文档校验规则表

> 配合 doc-blueprint skill 的 Checklist 第 7–8 步。
> 生成 `doc.md` 后，用本表逐项校验。每条规则直接引用 `doc-schema.md` 的字段名。两者是**契约关系**。
> 运行 `python skills/doc-blueprint/scripts/validate_doc.py doc.md`。

---

## 一、总则

### 严重级别
| 级别 | 含义 | 处理 |
|------|------|------|
| 🔴 ERROR | 硬性违规，蓝图不可交付 | 必须修复，阻断 |
| 🟡 WARNING | 质量缺陷 | 建议修复，不阻断但扣分 |

### 校验四组
- **结构 R-S**：必备章节是否齐全（按 `doc_type`）。
- **写作法则 R-W**：论断有证据 / 决策有理由 / 因果不跳步。
- **一致性 R-C**：数字同源 `datasets`、图表声明完整、口径齐全。
- **表现力 R-E**：block kind 合法、构造正确（反模式）。
- **意图 R-A**：`desired_action` 可判定、文体匹配。

### 质量评分
```
合格蓝图 = 所有 🔴 ERROR 通过  且  WARNING 通过率 ≥ 80%
质量分   = 通过规则数 / 适用规则数 × 100
```
> 适用规则按 `doc_type` 筛选（如 R-S 系列按各类型必备章节）。`validate_doc.py` 另执行 schema 级门禁（不计入规则数）：front-matter 必填字段齐全、`datasets` 必填、`sources` 必填且记录用户确认。

### 两层防线：规则（doc 内部）vs 对账（doc↔preview）
本规则表**只校验 `doc.md` 自身内部一致性**。`preview.md` 是否忠实投影（图表占位/状态/数字一一对应）由自审第 4、7 步 + 可选对账兜底。优先运行 `validate_doc.py`。

---

## 二、校验规则

### 意图（R-A）

#### R-A1 期望动作可判定 · 🔴 ERROR
- **检查**：`doc.desired_action` 非空，且是可观察动作（决策/执行/知晓/说服 + 可判定对象）。
- ❌ "让领导了解"　✅ "让领导周五前批准 50 万预算"

#### R-A2 文体匹配 · 🟡 WARNING
- **检查**：`doc.doc_type` 与 `desired_action` 匹配（审批→business_case/rfc；执行→runbook；知晓→weekly/changelog）。

---

### 结构（R-S）—— 按 `doc_type` 模板的必备章节

#### R-S1 必备章节齐全 · 🔴 ERROR
- **检查**：`doc_type` 模板列出的必备 slot，在正文 `<!-- doc:section slot= -->` 中全部出现。
- ❌ postmortem 缺 `root_cause`；rfc 缺 `alternatives`；prd 缺 `success_metrics`。
- > 无 `slot` 注释时，按标题语义匹配模板章节名；匹配不上判 🔴。

#### R-S2 每节有主旨 · 🟡 WARNING
- **检查**：每节 `intent` 非空；单节不超载多主旨（启发式：一节标题对应一条信息点组）。

---

### 写作法则（R-W）

#### R-W1 论断必有证据 · 🔴 ERROR
- **检查**：正文中的论断性表述（效果/性能/规模/对比判断）要么引用 `{{d:}}` / `[ref:]`，要么其相关 `datasets` 标 `confidence: assumed`。裸最高级（最优/最好/领先）判 🔴。
- ❌ "性能优秀"　✅ "P99 从 {{d:p99_before}} 降到 {{d:p99_after}}[ref:r2]"

#### R-W2 数字带口径 · 🔴 ERROR
- **检查**：每个 `datasets[]` 的 `caliber` 与 `source` 非空；正文引用的数字都有对应 `datasets`。

#### R-W3 决策必有理由 + 备选 · 🔴 ERROR
- **检查**：每个 `> [!decision]` 含"理由"；技术/方案决策（rfc/adr/prd/business_case）正文含至少一个备选方案与权衡。

#### R-W4 因果链显式 · 🟡 WARNING
- **检查**：从现象→根因、根因→改进的段落含显式因果连接（导致/因此/因为）；不跳步。

#### R-W5 无 placeholder · 🔴 ERROR
- **检查**：正文不含"TBD/待定/之后再说/适当展开/xxx"。真实未决问题写入"未决问题"段。

---

### 一致性（R-C）

#### R-C1 正文数字皆有源 · 🔴 ERROR
- **检查**：正文出现的每个数字都能对回某条 `datasets`（通过 `{{d:id}}` 插值或显式等值）。裸数字（不引用 datasets）判 🟡，并提示"是否应进 datasets"。

#### R-C2 图表数据有源 · 🔴 ERROR
- **检查**：每个 `figures[]` 的 `data_ref` 指向已声明 `datasets`（或 `inline`）；每个 ` ```chart/kpi ``` ` 块的 `id` 对应一条 `figures`。

#### R-C3 图表↔正文数字一致 · 🟡 WARNING
- **检查**：同一指标在图表 `data_ref` 与正文 `{{d:}}` 指向同一 `datasets.id`（不出现"正文引用 A，图引用 B 但 A≠B"）。

---

### 表现力（R-E）

#### R-E1 block kind 合法 · 🔴 ERROR
- **检查**：正文非纯文字块的标注 kind ∈ `doc-schema.md` 13 种枚举（chart:bar/line/pie、kpi、timeline、callout variant、status level、table intent 等）。枚举外判 🔴。

#### R-E2 图表反模式 · 🟡 WARNING
- **检查**：`chart:pie` 的分类 ≤5；无 3D/截断轴/双轴误导标记（启发式：pie 类目数）。pie >5 判 🔴。

#### R-E3 表格规范 · 🟡 WARNING
- **检查**：表格有表头行；数值列有单位提示（表头含单位或单元格带单位）。

#### R-E4 状态有图例 · 🔴 ERROR
- **检查**：使用 `[badge:...]` 的文档，首次出现处或在图/表旁有图例说明 level 含义；同 level 全文颜色含义一致。

---

## 三、规则汇总表

| 规则 | 组 | 级别 | 一句话 |
|------|----|------|--------|
| R-A1 | 意图 | 🔴 | 期望动作可判定 |
| R-A2 | 意图 | 🟡 | 文体匹配动作 |
| R-S1 | 结构 | 🔴 | 必备章节齐全 |
| R-S2 | 结构 | 🟡 | 每节有主旨 |
| R-W1 | 写作 | 🔴 | 论断必有证据 |
| R-W2 | 写作 | 🔴 | 数字带口径 |
| R-W3 | 写作 | 🔴 | 决策有理由+备选 |
| R-W4 | 写作 | 🟡 | 因果链显式 |
| R-W5 | 写作 | 🔴 | 无 placeholder |
| R-C1 | 一致 | 🔴 | 正文数字皆有源 |
| R-C2 | 一致 | 🔴 | 图表数据有源 |
| R-C3 | 一致 | 🟡 | 图表↔正文数字一致 |
| R-E1 | 表现 | 🔴 | block kind 合法 |
| R-E2 | 表现 | 🟡 | 图表反模式 |
| R-E3 | 表现 | 🟡 | 表格规范 |
| R-E4 | 表现 | 🔴 | 状态有图例 |

**共 16 条**：🔴 11 条（阻断），🟡 5 条（扣分）。

---

## 四、自修复策略

| 违规 | 常见修复 |
|------|----------|
| R-A1 动作不可判定 | 与用户确认具体可观察动作，回写 `desired_action`（必要时回 `clarify-doc`） |
| R-S1 缺必备章节 | 按模板补章节（如补"备选方案""根因"），补 `slot` 注释 |
| R-W1 论断无证据 | 引用 `datasets`/`references`，或标 `assumed`；删裸最高级 |
| R-W2 数字无口径 | 补 `caliber`/`source` |
| R-W3 决策无理由 | 补理由行 + 至少一个备选与权衡 |
| R-W5 placeholder | 替换为真实内容，或移入"未决问题" |
| R-C1/C2 数字/图表无源 | 声明进 `datasets`/`figures`，正文改用 `{{d:}}` 引用 |
| R-C3 图文数字矛盾 | 统一指向同一 `datasets.id` |
| R-E1 kind 非法 | 改为 13 种枚举内 kind |
| R-E2 pie>5 | 改 `chart:bar` 或合并小类 |
| R-E4 状态无图例 | 首次出现处加图例 |

> 自修复后**必须重跑** `validate_doc.py`，直到合格。修复记录写入 `doc.md` 校验报告段。

---

## 五、自审补充（Checklist 第 10 步，人工 + 脚本）

`validate_doc.py` 之外，人工新视角复查：

1. **论断-证据对账**：抽检 3-5 个论断，确认有证据或标 assumed。
2. **决策-理由对账**：每个 `[!decision]` 都有理由。
3. **数字一致性**：抽检图表/表格/正文同一指标，值一致。
4. **必备章节深度**：不只"有这节"，"必含"也写到位（如根因是系统性的，不是停在现场现象）。
5. **表现力反模式**：抽查"能用一句话说的对比却画了图"。
6. **意图标注完整**：每个非纯文字块都能对回 block kind。

发现问题就地修，修完回到第 7 步重校验。
