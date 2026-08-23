/**
 * Q3 述职报告图表数据层 —— 数字与 docs/2026-08-23-q3-ops-report/02-事实台账.md 同源
 * option 只是数据+意图，观感统一由 chartTheme.withTheme 注入
 */
import { CHART_TOKENS, pairBars, faintSplitLine, type EChartsOption } from '../theme/chartTheme'

/** 节 2 · 新增结构堆叠柱（付费渠道灰 / 裂变蓝，x 轴带总量） */
export const stackedNewUsers: EChartsOption = {
  xAxis: {
    type: 'category',
    data: ['Q2（共 10.4 万）', 'Q3（共 12.8 万）'],
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { fontSize: 15, color: CHART_TOKENS.label },
  },
  yAxis: { type: 'value', name: '新增（万）', ...faintSplitLine() },
  series: [
    {
      name: '付费渠道',
      type: 'bar',
      stack: 'total',
      data: [10.4, 10.7],
      itemStyle: { color: CHART_TOKENS.grey },
      barWidth: 92,
      label: { show: true, position: 'inside', color: CHART_TOKENS.label, fontWeight: 700, formatter: (p: any) => `${p.value} 万` },
    },
    {
      name: '裂变「暑期组队学」',
      type: 'bar',
      stack: 'total',
      data: [0, 2.1],
      itemStyle: { color: CHART_TOKENS.accent },
      label: { show: true, position: 'inside', color: '#fff', fontWeight: 700, formatter: (p: any) => (p.value ? `${p.value} 万` : '') },
    },
  ],
}

/** 节 2 · CAC 成对柱 */
export const cacPair: EChartsOption = pairBars(
  '混合获客成本',
  { label: 'Q2', value: 18.5, text: '18.5 元' },
  { label: 'Q3', value: 15.2, text: '15.2 元（−17.8%）' },
  'CAC（元）',
)

/** 节 3 · 活跃留存三指标（三 grid 各自量纲，改前灰/改后蓝） */
export const activeQuality: EChartsOption = {
  title: [
    { text: 'DAU（万）', left: '3%', top: 4, textStyle: { fontSize: 14, color: CHART_TOKENS.muted, fontWeight: 600 } },
    { text: '次月留存（%）', left: '36.3%', top: 4, textStyle: { fontSize: 14, color: CHART_TOKENS.muted, fontWeight: 600 } },
    { text: '推送点击率（%）', left: '69.6%', top: 4, textStyle: { fontSize: 14, color: CHART_TOKENS.muted, fontWeight: 600 } },
  ],
  grid: [
    { left: '4%', width: '24%', top: 40, bottom: 36 },
    { left: '37.3%', width: '24%', top: 40, bottom: 36 },
    { left: '70.6%', width: '24%', top: 40, bottom: 36 },
  ],
  xAxis: [0, 1, 2].map(i => ({
    type: 'category',
    gridIndex: i,
    data: ['Q2', 'Q3'],
    axisTick: { show: false },
    axisLine: { show: false },
    axisLabel: { fontSize: 14, color: CHART_TOKENS.label },
  })),
  yAxis: [0, 1, 2].map(i => ({ type: 'value', gridIndex: i, ...faintSplitLine() })),
  series: [
    mkPair(0, 4.2, 5.6, v => `${v} 万`),
    mkPair(1, 32, 41, v => `${v}%`),
    mkPair(2, 3.2, 8.7, v => `${v}%`),
  ],
}

function mkPair(gridIdx: number, before: number, after: number, fmt: (v: number) => string) {
  return {
    type: 'bar',
    xAxisIndex: gridIdx,
    yAxisIndex: gridIdx,
    barWidth: 54,
    data: [
      { value: before, itemStyle: { color: CHART_TOKENS.grey },
        label: { show: true, position: 'top', color: CHART_TOKENS.muted, fontWeight: 700, formatter: () => fmt(before) } },
      { value: after, itemStyle: { color: CHART_TOKENS.accent },
        label: { show: true, position: 'top', color: CHART_TOKENS.accent, fontWeight: 700, formatter: () => fmt(after) } },
    ],
  }
}
