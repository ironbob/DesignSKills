/**
 * 统一图表主题层 —— 「图表观感不稳」的解法：
 * 每张图的 option 经过 withTheme() 注入同一套字号/配色/网格/标签规范，
 * 组件层（FigureChart）不再各自发挥。
 */
export const CHART_TOKENS = {
  accent: '#2563EB',
  grey: '#CBD5E1',
  label: '#475569',
  muted: '#64748B',
  grid: '#E2E8F0',
  good: '#16A34A',
  fontFamily: `-apple-system, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif`,
}

export interface EChartsOption {
  [key: string]: any
}

/** 合并统一主题（文本/配色/动画/网格基线），不覆盖调用方已显式设置的键 */
export function withTheme(option: EChartsOption): EChartsOption {
  return {
    animation: false,
    textStyle: { fontFamily: CHART_TOKENS.fontFamily, color: CHART_TOKENS.label },
    color: option.color ?? [CHART_TOKENS.accent, CHART_TOKENS.grey, CHART_TOKENS.muted, CHART_TOKENS.good],
    grid: { top: 36, bottom: 8, left: 8, right: 8, containLabel: true, ...(option.grid ?? {}) },
    ...option,
  }
}

/** 基线网格样式（y 轴淡网格） */
export function faintSplitLine() {
  return { splitLine: { lineStyle: { color: CHART_TOKENS.grid } } }
}

/** Q2/Q3 成对柱通用构造：改前灰、改后蓝、值直接标注 */
export function pairBars(
  name: string,
  before: { label: string; value: number; text: string },
  after: { label: string; value: number; text: string },
  yName: string,
): EChartsOption {
  return {
    xAxis: {
      type: 'category',
      data: [before.label, after.label],
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { fontSize: 15, color: CHART_TOKENS.label },
    },
    yAxis: { type: 'value', name: yName, ...faintSplitLine() },
    series: [
      {
        type: 'bar',
        name,
        barWidth: 92,
        data: [
          { value: before.value, itemStyle: { color: CHART_TOKENS.grey },
            label: { show: true, position: 'top', color: CHART_TOKENS.muted, fontWeight: 700, formatter: () => before.text } },
          { value: after.value, itemStyle: { color: CHART_TOKENS.accent },
            label: { show: true, position: 'top', color: CHART_TOKENS.accent, fontWeight: 700, formatter: () => after.text } },
        ],
      },
    ],
  }
}
