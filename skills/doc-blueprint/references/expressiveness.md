# 表现力组件库：图表 / 表格 / 状态怎么正确用

> 配合 doc-blueprint skill 的 Checklist 第 6 步（表现力选型）。
> 这是 `doc-schema.md` block kind 枚举的**选用说明书**：每个 block kind **何时用、怎么造对、踩什么坑**。
> 与 `doc-schema.md` 的 block kind 表（13 种）、`doc-render` 各后端 `component-mapping.md` 同进同退。
>
> 核心原则：**意图先于承载**。先问"这块内容要让人看的是什么"（看数 / 看趋势 / 看状态 / 被警示），再选 block kind，最后造数据。不要"为了好看"而上图。

---

## 一、选用法则（选对 kind）

按"读者要从中看出什么"决策：

| 读者要看的 | 选 kind | 理由 |
|-----------|---------|------|
| 精确数值 / 多维对照查表 | `table` | 表格能精确读数、对照 |
| 量级对比（离散类目谁多谁少） | `chart:bar` | 柱长一眼比大小 |
| 趋势（随时间/序列的变化） | `chart:line` | 折线显走势 |
| 占比（整体由几部分构成，≤5 类） | `chart:pie` | 饼图显份额（慎用，见反模式） |
| 单一状态需一眼扫读 | `status` | 徽章/颜色比文字快 |
| 多维状态矩阵（N 项 × 状态） | `table`（intent=status_board） | 一张表看全貌 |
| 关键指标头图（一个核心数字） | `kpi` | 大数字 + 对比，高管友好 |
| 时序事件（先发生什么后发生什么） | `timeline` | 时间线显因果顺序 |
| 结构 / 流程 / 时序关系 | `diagram`（mermaid） | 图显关系，文字难表达 |
| 强调一句话 / 警示 / 决策 | `callout` | 视觉跳出正文，不被淹没 |
| 叙述因果 / 论证 | `prose` | 默认形态 |

### 反过度可视化（最重要的取舍）
- **≤3 个值对比 → 直接 `prose`**：增长 18%、A 比 B 高 2 倍，一句话说完，别画图。图为"多维/趋势"而存在，不是装饰。
- **单一数字 → `kpi` 或直接写**：不要为"营收 1.2 亿"画饼图。
- **能查表的精确值，不要硬画图**：若读者要"Q3 华东区具体多少"，给表不给柱状。
- **状态 ≥4 项才上表/矩阵**：一两个状态直接 `status` 行内徽章。

---

## 二、各 block kind 构造规范 + 反模式

### `chart:bar` / `chart:line` / `chart:pie`

**构造规范**：
- 必须有 `id`（指向 `figures[]`）、`data_ref`（指向 `datasets[]`）、`title`。
- 数据带口径：图表标题或 `figures[].note` 写明"什么口径、什么时点"。
- 坐标轴有含义：bar 的类目轴、line 的时间轴、pie 的分类，都要可读。

**反模式（校验 R-E 拦截或自审 catch）**：
| ❌ 错误 | ✅ 正确 |
|--------|--------|
| 饼图 >5 片 / 含"其他"杂烩片 | 改 `chart:bar`，或合并小类 |
| 3D 图 / 截断 y 轴 / 双轴误导 | 用 2D、y 轴从 0 起、慎用双轴并标注 |
| 折线画分类数据 / 柱状画时间序列 | 分类→bar，时序→line |
| 图与正文数字不一致 | 统一引用 `datasets`，禁各自硬编码 |
| 图表无标题/无口径 | 补 title + caliber |

### `table`

**构造规范**：
- 必有表头行；数值列带单位（表头或单元格）。
- 行列有序：按某列（大小/时间/优先级）排序，不要随机。
- 复杂表（决策矩阵/状态板）用 `<!-- doc:intent=... -->` 标注意图。
- 大表考虑：>10 行拆分或加"小结"行。

**反模式**：
| ❌ 错误 | ✅ 正确 |
|--------|--------|
| 无表头 / 无单位 | 补表头，数值标单位 |
| 单元格塞长段落 | 长内容拆成 `prose` + 小表 |
| 用表表达流程（一格一格读） | 流程用 `diagram` 或 `list` |
| 表里数字与 `datasets` 矛盾 | 统一引用 |

### `status`（`[badge:L text]`）

**构造规范**：
- level 枚举：`healthy | degraded | down | blocked | done | todo`。
- **必须有图例**：首次出现某 level 时，或在图/表旁注明"绿=已恢复/黄=降级/红=故障"。
- 颜色含义全文一致：同一 level 不能这页绿那页红。

**反模式**：
| ❌ 错误 | ✅ 正确 |
|--------|--------|
| 用状态却无图例 | 首次出现处加图例 |
| 颜色含义冲突（degraded 时绿时黄） | 全文一致 |
| 滥用状态徽章替代说明 | 状态只标"单一可扫读状态"，细节用 prose |

### `kpi`

**构造规范**：
- `value_ref` + `label` 必填；`delta_ref`（对比基准，如环比/目标）推荐。
- 一个 KPI 头图只承一个核心指标；多个并排成行（`figures` 多条）。

**反模式**：把 KPI 当装饰堆砌；KPI 数字与正文/表不一致（统一引用 `datasets`）。

### `callout`（`> [!variant]`）

**构造规范**：
- variant：`note`（补充）/ `tip`（建议）/ `warning`（风险）/ `important`（强调）/ `decision`（决策，**必带理由**）。
- 一条 callout 一个主旨；别把整段正文塞进 callout。

**反模式**：
| ❌ 错误 | ✅ 正确 |
|--------|--------|
| `[!decision]` 只给结论不给理由 | 补理由 + 至少一个备选（R-W3） |
| 滥用 warning（全篇都警示=没有警示） | warning 只用于真风险 |
| 把核心论点藏进 callout | 核心论点用 `prose`/标题，callout 只强调 |

### `diagram`（mermaid）

**构造规范**：
- 流程用 `flowchart`、时序用 `sequenceDiagram`、状态用 `stateDiagram`。
- 节点文字简短；复杂图拆分或配文字说明。

**反模式**：用图表达本该用表/列表的精确数据；图里信息与正文冲突。

### `timeline`

**构造规范**：
- 用 ` ```timeline ``` ` 块或表格；每条含"时间 + 事件 + （可选）影响"。
- 按时间正序；关键节点高亮。

---

## 三、数字一致性（`datasets` 单一源，= EPPS `sample_state`）

图表"用错"最常见的不是选错图，而是**图里的数和正文说的数对不上**。

**硬规则**：
- 所有数字先声明进 `datasets`（值/单位/口径/来源）。
- 正文用 `{{d:<id>}}` 插值；图表 `data_ref` 指向 `datasets`；表格数字引用同一 `datasets`。
- 同一指标全文只有一个真值、一个口径。校验 R-C1/R-C2 强制；自审第 4 步对账"图表↔表格↔正文"。

**示例**：
```yaml
datasets:
  - { id: affected_orders, value: 1284, unit: 单, caliber: "6/14 00:00–02:30 支付超时失败订单", source: 支付中台告警, confidence: measured }
  - { id: duration_min, value: 150, unit: 分钟, caliber: "首个告警到完全恢复", source: 值班记录, confidence: measured }
```
```markdown
本次事故影响 {{d:affected_orders}} 单订单，持续 {{d:duration_min}} 分钟。
（图表 data_ref: affected_orders → 图里也是 1284，不会漂移成 1300）
```

---

## 四、受众调表现力（输入来自 brief）

`doc.audience`（来自上游 brief）是表现力选型的关键输入：
- **高管/决策者** → 偏 `kpi` 头图、趋势 `chart:line`、`callout decision`；少而精。
- **工程师/执行者** → 偏 `table`、`code`、`diagram`；精确可操作。
- **外部用户** → 偏 `prose`、`status`、`callout`；少术语、多"对你意味着什么"。

> 受众在 `clarify-doc` 锁定，作为约束传到这里。表现力横跨 blueprint（选型+构造+一致性），不进 clarify（clarify 只决定"给谁看"）。
