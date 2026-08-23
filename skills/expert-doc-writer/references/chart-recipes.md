# 图表数据层配方（chart recipes）

阶段 6/7 写 `doc-renderer/.vitepress/data/<slug>.charts.ts` 时使用。**选型判据在 `visual-form-catalog.md`（T5–T9）**，本文件管"选型定了之后怎么写"：常用图形状有骨架，写法不依赖任何历史示例文件。配方来自两次校准运行（已删语料，存于 git 历史），此处是它们的可复用沉淀。

## 纪律（先于一切配方）

1. **option 只写数据与意图**：类目、系列、标注文案、排序。颜色/字号经 `CHART_TOKENS` 常量引用，观感基线由 `withTheme()` 注入（FigureChart 内部调用，数据层不重复调）；
2. **数字与 02-事实台账逐位同源**：图上每个数（含标注文案里的）都能在台账找到条目；**图示补数也算数字**——如堆叠图"其余=100−X"要先在台账记推算条目（F-x，推算档）再入图；
3. **换算值进标注**：降幅/pp/相对变化在柱端标注里给出，但口径行（source）注明"推算档"与换算式；
4. 段内白字 `#fff`（强调色段上的文字）是唯一历史豁免的裸色值。

## 内建构造器（`theme/chartTheme.ts`，直接调用）

### `rankBars(bars, xName, max?)` — 排序横向柱（T6 单指标排序）

```ts
import { rankBars } from '../theme/chartTheme'
export const perf: EChartsOption = rankBars(
  [ // 升序传入 = 最大值置顶
    { label: '库体积', value: 17, text: '-17%' },
    { label: '查询提速', value: 65, text: '-65%', emphasize: true }, // 重点柱强调蓝
  ],
  '改善幅度（%）',
)
```

适用：一个指标多个分类的对比排序。类目名 >6 字自动适合横向；值标柱端不用 x 轴读数。

### `pairBars(name, before, after, yName)` — 前后成对柱（单指标两期）

```ts
export const cac: EChartsOption = pairBars(
  '混合获客成本',
  { label: 'Q2', value: 18.5, text: '18.5 元' },
  { label: 'Q3', value: 15.2, text: '15.2 元（−17.8%）' },
  'CAC（元）',
)
```

适用：**单个**指标的前后对比（改前灰/改后蓝）。多指标见下两形。

## 数据层本地形状（无内建构造器，照骨架写）

### 形状 A：多 grid 小倍数 —— 多指标同比、量纲互异

**何时用**：2–4 个指标的基期/当期对比，量纲不同（条 / 元 / % / 评分）。任何同轴方案（归一化指数、双 y 轴）都会牺牲可读性。
**何时不该**：指标 >4（改 T11 紧凑表）；量纲相同（改形状 B）；有月度序列（T7 折线）。

```ts
import { CHART_TOKENS, faintSplitLine, type EChartsOption } from '../theme/chartTheme'

export const quality: EChartsOption = {
  title: [0, 1, 2].map(i => ({
    text: ['MQL（条）', 'CPL（元）', '转化率（%）'][i],   // 每 grid 一行"指标（单位）"
    left: `${3 + i * 32}%`, top: 4,
    textStyle: { fontSize: 13.5, color: CHART_TOKENS.muted, fontWeight: 600 },
  })),
  grid: [0, 1, 2].map(i => ({ left: `${3 + i * 32}%`, width: '26%', top: 36, bottom: 30 })),
  xAxis: [0, 1, 2].map(i => ({
    type: 'category', gridIndex: i, data: ['2025 H1', '2026 H1'],
    axisTick: { show: false }, axisLine: { show: false },
    axisLabel: { fontSize: 13.5, color: CHART_TOKENS.label },
  })),
  yAxis: [0, 1, 2].map(i => ({ type: 'value', gridIndex: i, ...faintSplitLine() })),
  series: [ mkPair(0, 3319, 4680, ...), mkPair(1, 320, 245, ...), ... ],
}
// 每 grid 一个 series：before 灰 / after 强调蓝，值标柱端（formatter 闭包给标注文案）
function mkPair(gridIdx: number, before: number, after: number, fmt: (v: number) => string) { ... }
```

要点：grid 等宽分布（left 按 `3 + i*间距` 推）；标注文案带同比（`4,680（+41%）`），推算基期（如 `≈3,319`）在 source 行注明。

### 形状 B：率类分组柱 —— 2–3 个同量纲指标的两期对比

**何时用**：全部指标同为 %（或同单位），双系列（基期灰/当期蓝）并排。
**何时不该**：量纲互异（改形状 A）；单指标（改 `pairBars`）。

```ts
export const retention: EChartsOption = {
  legend: { show: true, top: 0, right: 8 },          // 极简 legend：值标注为主、legend 为辅
  xAxis: { type: 'category', data: ['客户续费率', '净收入留存率 NDR'], ... },
  yAxis: { type: 'value', name: '%', max: 125, ...faintSplitLine() },  // max 留标注空间
  series: [
    { name: '2025 H1', type: 'bar', barWidth: 64, itemStyle: { color: CHART_TOKENS.grey },
      data: [88, 104].map(...) },                    // 每数据点带 label: position top
    { name: '2026 H1', type: 'bar', barWidth: 64, itemStyle: { color: CHART_TOKENS.accent },
      data: [...] },                                 // 标注含 pp：'93%（+5pp）'
  ],
}
```

### 形状 C：堆叠横条 —— 构成占比 + 两期对比（T8 首选形态）

**何时用**：≤5 类构成、且要看占比变化；占比与总量一图同读。
**何时不该**：>5 类（Top4+其他）；单一时点且类目少（可环形）；趋势（T7）。

```ts
export const mix: EChartsOption = {
  grid: { left: 8, right: 8, top: 14, bottom: 8, containLabel: true },
  xAxis: { type: 'value', max: 100, axisLabel: { show: false }, splitLine: { show: false } },
  yAxis: { type: 'category', inverse: true, data: ['2025 H1', '2026 H1'], ... }, // inverse=最新在上
  series: [
    { name: '渠道贡献', type: 'bar', stack: 'arr', barWidth: 44,
      itemStyle: { color: CHART_TOKENS.accent },     // 强调段蓝+段内白字
      data: [12, 23].map(...) },                     // label position 'inside'
    { name: '直销及其他', type: 'bar', stack: 'arr',
      itemStyle: { color: CHART_TOKENS.grey },       // 灰阶段+段内深字
      data: [88, 77].map(...) },                     // ← 补数：先回填台账推算条目
  ],
}
```

## 反配方（出现即 crit ⑥ 违例）

- Mermaid 画数据图 / ECharts 画结构图（工具分工红线，见 SKILL.md）；
- option 手写系列色 hex 裸值（`#fff` 段内白字豁免除外）；
- 为单篇新形状加全局构造器——**单篇形状留在本文档数据层，≥2 篇复用再提升进 `chartTheme.ts`**（过早抽象增加维护面）；
- 图例依赖（无值标注、读者须往返图例才能读数）；
- 两点画折线（T7 纪律：两个时点用柱/条，不画折线）。

## 复用提升规则

形状 A/B/C 目前是骨架（照抄改数），不是构造器。判断标准：**第二种文档用到同一形状时**，把参数差异（grid 数、系列名、标注 formatter）抽成构造器进 `chartTheme.ts`，并在本文件把对应小节改为构造器用法——本文件与 chartTheme 同步演进。
