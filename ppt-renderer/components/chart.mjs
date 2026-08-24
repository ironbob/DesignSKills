// 图表件：storyboard chart spec → pptxgenjs 原生图表（PowerPoint/WPS 中可编辑，非图片）
// 数字只允许来自 facts 解析层（builders/resolve.mjs 已把 factValues 换成数值+display）
import { COLOR, FONT } from './tokens.mjs'

const AXIS_BASE = {
  valAxisHidden: true,
  valAxisLineShow: false,
  catAxisLineShow: false,
  valGridLine: { style: 'none' },
  catGridLine: { style: 'none' },
  showLegend: false,
  showTitle: false,
  dataLabelFontFace: FONT.sans,
  catAxisLabelFontFace: FONT.sans,
  catAxisLabelColor: COLOR.label,
  shadow: { type: 'none' },
}

/**
 * metricsBar：N 个指标各一 mini 柱图（25 灰 / 26 蓝，值标柱端）——四指标同比用
 * spec.metrics: [{label, baselineFact, currentFact, format}]；spec.catLabels: 类目标签对（默认 [25 H1, 26 H1]）
 */
export function metricsBar(pl, pres, spec, box) {
  const n = spec.metrics.length
  const labelH = 0.24
  const gap = 0.18
  const subW = (box.w - gap * (n - 1)) / n
  spec.metrics.forEach((m, i) => {
    const x = box.x + i * (subW + gap)
    pl.text(m.label, {
      x, y: box.y, w: subW, h: labelH,
      fontSize: 10.5, fontFace: FONT.sans, color: COLOR.muted, bold: true,
      align: 'center', valign: 'middle', inset: 0,
    }, 'fg', `chart-metric-label-${i}`)
    pl.chart(pres, pl.slide, pres.ChartType.bar, [
      { name: m.label, labels: spec.catLabels ?? ['25 H1', '26 H1'], values: [m.baseline, m.current] },
    ], {
      x, y: box.y + labelH + 0.04, w: subW, h: box.h - labelH - 0.04,
      barDir: 'col', chartColors: [COLOR.grey, COLOR.accent],
      barGapWidthPct: 42,
      showValue: true,
      dataLabelFormatCode: m.format, dataLabelPosition: 'outEnd',
      dataLabelFontSize: 10.5, dataLabelColor: COLOR.label, dataLabelFontBold: true,
      catAxisLabelFontSize: 9.5,
      ...AXIS_BASE,
    }, `chart-metric-${i}`)
  })
}

/** groupedBar：labels × 2 series（25 灰 / 26 蓝）——留存率类同比用 */
export function groupedBar(pl, pres, spec, box) {
  pl.chart(pres, pl.slide, pres.ChartType.bar, spec.series.map(s => ({
    name: s.name, labels: spec.labels, values: s.values,
  })), {
    x: box.x, y: box.y, w: box.w, h: box.h,
    barDir: 'col', chartColors: [COLOR.grey, COLOR.accent],
    barGapWidthPct: 80, barOverlapPct: -12,
    showValue: true,
    dataLabelFormatCode: spec.format, dataLabelPosition: 'outEnd',
    dataLabelFontSize: 11, dataLabelColor: COLOR.label, dataLabelFontBold: true,
    catAxisLabelFontSize: 11,
    ...AXIS_BASE,
    showLegend: true, legendPos: 'b', legendFontSize: 10, legendFontFace: FONT.sans, legendColor: COLOR.label,
  }, 'chart-grouped')
}

/** stackedHBar：横向堆叠占比（渠道/直销，段内白字） */
export function stackedHBar(pl, pres, spec, box) {
  pl.chart(pres, pl.slide, pres.ChartType.bar, spec.segments.map(sg => ({
    name: sg.name, labels: spec.rows.map(r => r.label), values: sg.values,
  })), {
    x: box.x, y: box.y, w: box.w, h: box.h,
    barDir: 'bar', barGrouping: 'stacked',
    chartColors: spec.segments.map(sg => sg.tone === 'accent' ? COLOR.accent : COLOR.greyDeep),
    barGapWidthPct: 55,
    showValue: true,
    dataLabelFormatCode: spec.format, dataLabelPosition: 'ctr',
    dataLabelFontSize: 10.5, dataLabelColor: 'FFFFFF', dataLabelFontBold: true,
    catAxisLabelFontSize: 10.5,
    ...AXIS_BASE,
    showLegend: true, legendPos: 'b', legendFontSize: 10, legendFontFace: FONT.sans, legendColor: COLOR.label,
  }, 'chart-stacked')
}

export function renderChart(pl, pres, spec, box) {
  if (spec.type === 'metricsBar') return metricsBar(pl, pres, spec, box)
  if (spec.type === 'groupedBar') return groupedBar(pl, pres, spec, box)
  if (spec.type === 'stackedHBar') return stackedHBar(pl, pres, spec, box)
  throw new Error(`未知图表类型: ${spec.type}`)
}
