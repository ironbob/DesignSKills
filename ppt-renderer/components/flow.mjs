// 流程件：storyboard flow spec → 原生形状 + 箭头（可在 PowerPoint/WPS 里逐节点编辑）
import { COLOR, FONT, TYPE } from './tokens.mjs'
import { panel } from './chrome.mjs'

/**
 * 双排流程（机制页用）：每排 = 行标签 + N 个节点 + 箭头
 * spec.rows: [{label, steps:[{label, sub?, tone?}]}]
 */
export function flowRows(pl, spec, box) {
  const n = spec.rows.length
  const gapY = 0.34
  const rowH = (box.h - gapY * (n - 1)) / n
  spec.rows.forEach((row, ri) => {
    const y = box.y + ri * (rowH + gapY)
    // 行标签（左侧窄条，避免占横向空间）
    pl.text(row.label, {
      x: box.x, y: y + 0.02, w: 0.52, h: rowH,
      fontSize: 10, fontFace: FONT.sans, color: COLOR.accent, bold: true,
      align: 'left', valign: 'top', inset: 0,
    }, 'fg', `flow-rowlabel-${ri}`)
    const steps = row.steps
    const innerX = box.x + 0.62
    const innerW = box.x + box.w - innerX
    const arrowW = 0.30
    const nodeW = (innerW - arrowW * (steps.length - 1)) / steps.length
    steps.forEach((st, si) => {
      const x = innerX + si * (nodeW + arrowW)
      const tone = st.tone === 'good' ? COLOR.good : st.tone === 'accent' ? COLOR.accent : COLOR.accent
      panel(pl, {
        x, y, w: nodeW, h: rowH,
        fill: st.tone ? (st.tone === 'good' ? COLOR.goodSoft : COLOR.accentSoft) : COLOR.paper,
        lineColor: COLOR.grid,
      })
      if (st.tone) {
        pl.shape(pl.slide, 'rect', {
          x, y: y + 0.05, w: nodeW, h: 0.03,
          fill: { color: tone }, line: { type: 'none' },
        }, 'bg', `flow-tone-${ri}-${si}`)
      }
      const hasSub = Boolean(st.sub)
      pl.text(st.label, {
        x: x + 0.06, y: y + (hasSub ? 0.04 : 0), w: nodeW - 0.12, h: hasSub ? rowH * 0.38 : rowH,
        fontSize: TYPE.step, fontFace: FONT.sans, color: COLOR.ink, bold: true,
        align: 'center', valign: hasSub ? 'top' : 'middle', inset: 0.02,
      }, 'fg', `flow-step-${ri}-${si}`)
      if (hasSub) {
        pl.text(st.sub, {
          x: x + 0.06, y: y + rowH * 0.52, w: nodeW - 0.12, h: rowH * 0.44,
          fontSize: TYPE.stepSub, fontFace: FONT.sans, color: COLOR.label,
          align: 'center', valign: 'top', inset: 0.02,
        }, 'fg', `flow-sub-${ri}-${si}`)
      }
      if (si < steps.length - 1) {
        pl.shape(pl.slide, 'rightArrow', {
          x: x + nodeW + 0.04, y: y + rowH / 2 - 0.11, w: arrowW - 0.08, h: 0.22,
          fill: { color: COLOR.muted }, line: { type: 'none' },
        }, 'bg', `flow-arrow-${ri}-${si}`)
      }
    })
  })
  if (spec.linkNote) {
    pl.text(spec.linkNote, {
      x: box.x + 0.62, y: box.y + box.h + 0.06, w: box.w - 0.62, h: 0.26,
      fontSize: 10, fontFace: FONT.sans, color: COLOR.muted, italic: true,
      align: 'left', valign: 'middle', inset: 0,
    }, 'fg', 'flow-linknote')
  }
}
