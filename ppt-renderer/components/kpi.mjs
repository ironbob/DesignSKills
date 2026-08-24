// KPI 大数字件：数值 + 指标名 + 同比角标（ExecSummary 右侧栅格用）
import { COLOR, FONT, TYPE } from './tokens.mjs'

/**
 * 单个 KPI 单元格（无卡片底——编辑版式里是栅格不是卡片堆砌）
 * fact 解析后的 spec: {label, display, baselineDisplay?, deltaDisplay?, deltaTone}
 */
export function kpiCell(pl, { x, y, w, h, kpi }) {
  const toneColor = kpi.deltaTone === 'risk' ? COLOR.risk : COLOR.good
  const value = /^[\d.]+$/.test(String(kpi.value)) ? Number(kpi.value).toLocaleString('en-US') : kpi.value
  pl.text([
    { text: String(value), options: { fontSize: TYPE.kpi, color: COLOR.accent, bold: true, fontFace: FONT.latin } },
    ...(kpi.unit ? [{ text: ` ${kpi.unit}`, options: { fontSize: 13, color: COLOR.muted, bold: true, fontFace: FONT.sans } }] : []),
  ], {
    x, y, w, h: h * 0.52, fontSize: TYPE.kpi,   // opts.fontSize=设计字号（run 覆盖渲染，几何记录用）
    fontFace: FONT.latin, align: 'left', valign: 'bottom', inset: 0,
  }, 'fg', 'kpi-value')
  pl.text([
    { text: kpi.label, options: { fontSize: TYPE.kpiLabel, color: COLOR.label, bold: true } },
    ...(kpi.deltaDisplay ? [{
      text: `  ${kpi.deltaDisplay}`, options: { fontSize: TYPE.kpiDelta, color: toneColor, bold: true },
    }] : []),
  ], {
    x, y: y + h * 0.58, w, h: h * 0.42, fontSize: TYPE.kpiLabel,
    fontFace: FONT.sans, align: 'left', valign: 'top',
  }, 'fg', 'kpi-label')
}
