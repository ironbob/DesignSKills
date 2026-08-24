// 版式 2/7 · 管理层摘要：左论点+问题+ask，右 2×2 KPI 栅格
// 版式语义：thesis/risks/kpis/ask 四模块并存时 thesis ≤48 字（长 thesis 必须拆页，gate 1 拦截）
import { COLOR, FONT, TYPE } from '../components/tokens.mjs'
import { titleBlock, sourceFooter, accentPanel, COMMON_FONT_SPEC } from '../components/chrome.mjs'
import { kpiCell } from '../components/kpi.mjs'

export const FONT_SPEC = {
  ...COMMON_FONT_SPEC,
  'es-thesis': TYPE.thesis, 'es-risk-head': 11, 'es-risks': 12, 'es-ask': 12,
  'kpi-value': TYPE.kpi, 'kpi-label': TYPE.kpiLabel,
}
export const HERO_NAMES = ['kpi-value', 'kpi-label']
export const KEY_ELEMENTS = [{ prefix: 'kpi-value', min: 20, bold: true }]

export function render({ pl, spec, pageNo, total }) {
  titleBlock(pl, { tag: spec.tag ?? '管理层摘要', title: spec.title })
  sourceFooter(pl, { source: spec.source, pageNo, total })

  // 左列：论点 → 问题预告 → ask
  pl.text(spec.thesis, {
    x: 0.5, y: 1.48, w: 4.3, h: 1.38,
    fontSize: TYPE.thesis, fontFace: FONT.sans, color: COLOR.label,
    align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.28,
  }, 'fg', 'es-thesis')
  pl.text('结构性问题（已备 H2 收口计划）', {
    x: 0.5, y: 2.98, w: 4.3, h: 0.24,
    fontSize: 11, fontFace: FONT.sans, color: COLOR.risk, bold: true,
    align: 'left', valign: 'middle', inset: 0.02,
  }, 'fg', 'es-risk-head')
  const riskRuns = []
  spec.risks.forEach((r, i) => {
    if (i) riskRuns.push({ text: '\n', options: { breakType: 'para' } })
    riskRuns.push({ text: '● ', options: { color: COLOR.risk, fontSize: 9, bold: true } })
    riskRuns.push({ text: r, options: { color: COLOR.label, fontSize: 12 } })
  })
  pl.text(riskRuns, {
    x: 0.5, y: 3.26, w: 4.3, h: 0.82, fontSize: 12,   // opts.fontSize=设计字号（run 覆盖渲染，几何记录用）
    fontFace: FONT.sans, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.22,
  }, 'fg', 'es-risks')
  accentPanel(pl, { x: 0.5, y: 4.2, w: 4.3, h: 0.62, barColor: COLOR.accent, fill: COLOR.accentSoft })
  pl.text(`需要您决定：${spec.ask}`, {
    x: 0.66, y: 4.22, w: 4.05, h: 0.58,
    fontSize: 12, fontFace: FONT.sans, color: COLOR.accent, bold: true,
    align: 'left', valign: 'middle', inset: 0.02,
  }, 'fg', 'es-ask')

  // 右列：2×2 KPI 栅格（≤4 由 gate 1 拦截超量，不做 slice 静默截断）
  const cellW = 2.1, cellH = 1.55, gx = 5.1, gy = 1.55, gap = 0.15
  spec.kpis.forEach((kpi, i) => {
    const cx = gx + (i % 2) * (cellW + gap)
    const cy = gy + Math.floor(i / 2) * (cellH + gap + 0.05)
    kpiCell(pl, { x: cx, y: cy, w: cellW, h: cellH, kpi })
  })
}
