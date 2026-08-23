// 版式 5/6 · 风险—行动：左问题（表现·根因）→ 箭头 → 右 H2 收口行动（Owner·截止）
import { COLOR, FONT } from '../components/tokens.mjs'
import { titleBlock, sourceFooter, accentPanel } from '../components/chrome.mjs'

export function render({ pl, spec, pageNo, total }) {
  titleBlock(pl, { tag: spec.tag ?? '问题与 H2 行动', title: spec.title })
  sourceFooter(pl, { source: spec.source, pageNo, total })

  pl.text('结构性问题（表现 · 根因）', {
    x: 0.5, y: 1.42, w: 4.0, h: 0.24,
    fontSize: 11, fontFace: FONT.sans, color: COLOR.muted, bold: true, align: 'left', valign: 'middle', inset: 0.02,
  }, 'fg', 'ra-head-left')
  pl.text('H2 收口行动（Owner · 截止）', {
    x: 5.3, y: 1.42, w: 4.2, h: 0.24,
    fontSize: 11, fontFace: FONT.sans, color: COLOR.muted, bold: true, align: 'left', valign: 'middle', inset: 0.02,
  }, 'fg', 'ra-head-right')

  const rows = spec.pairs.slice(0, 2)
  const rowH = 1.44
  rows.forEach((p, i) => {
    const y = 1.74 + i * (rowH + 0.14)
    accentPanel(pl, { x: 0.5, y, w: 4.0, h: rowH, barColor: COLOR.risk, fill: COLOR.riskSoft })
    pl.text(p.risk.what, {
      x: 0.66, y: y + 0.1, w: 3.72, h: 0.34,
      fontSize: 13, fontFace: FONT.sans, color: COLOR.ink, bold: true, align: 'left', valign: 'top', inset: 0.02,
    }, 'fg', `ra-risk-${i}`)
    pl.text(p.risk.evidence, {
      x: 0.66, y: y + 0.5, w: 3.72, h: 0.86,
      fontSize: 11.5, fontFace: FONT.sans, color: COLOR.label, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.22,
    }, 'fg', `ra-risk-ev-${i}`)

    pl.shape(pl.slide, 'rightArrow', {
      x: 4.58, y: y + rowH / 2 - 0.14, w: 0.52, h: 0.28,
      fill: { color: COLOR.muted }, line: { type: 'none' },
    }, 'bg', `ra-arrow-${i}`)

    accentPanel(pl, { x: 5.3, y, w: 4.2, h: rowH, barColor: COLOR.good, fill: COLOR.goodSoft })
    pl.text(p.action.what, {
      x: 5.46, y: y + 0.1, w: 3.9, h: 0.34,
      fontSize: 13, fontFace: FONT.sans, color: COLOR.ink, bold: true, align: 'left', valign: 'top', inset: 0.02,
    }, 'fg', `ra-action-${i}`)
    pl.text(`Owner：${p.action.owner}\n截止：${p.action.deadline}`, {
      x: 5.46, y: y + 0.46, w: 3.9, h: 0.46,
      fontSize: 10.5, fontFace: FONT.sans, color: COLOR.good, bold: true, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.2,
    }, 'fg', `ra-owner-${i}`)
    pl.text(p.action.detail, {
      x: 5.46, y: y + 0.95, w: 3.9, h: 0.44,
      fontSize: 11.5, fontFace: FONT.sans, color: COLOR.label, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.2,
    }, 'fg', `ra-detail-${i}`)
  })
}
