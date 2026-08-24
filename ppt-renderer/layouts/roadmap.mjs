// 版式 7/7 · 规划：≤3 条工作流（what·里程碑·Owner）
// 版式语义：不得承载资源申请字段（target/baseline/resources/requests/askLine 属 decision-ask，gate 1 拦截）
import { COLOR, FONT } from '../components/tokens.mjs'
import { titleBlock, sourceFooter, panel, COMMON_FONT_SPEC } from '../components/chrome.mjs'

export const FONT_SPEC = {
  ...COMMON_FONT_SPEC,
  'rm-idx': 26, 'rm-what': 14, 'rm-milestone': 12, 'rm-owner': 11, 'rm-linknote': 10.5,
}
export const HERO_NAMES = ['rm-what', 'rm-milestone', 'rm-owner']
export const KEY_ELEMENTS = [{ prefix: 'rm-what', min: 12, bold: true }]

export function render({ pl, spec, pageNo, total }) {
  titleBlock(pl, { tag: spec.tag ?? '规划', title: spec.title })
  sourceFooter(pl, { source: spec.source, pageNo, total })

  const n = spec.workstreams.length
  const gap = 0.22
  const cardW = (9.0 - gap * (n - 1)) / n
  spec.workstreams.forEach((w, i) => {
    const x = 0.5 + i * (cardW + gap)
    panel(pl, { x, y: 1.56, w: cardW, h: 2.72 })
    pl.text(`0${i + 1}`, {
      x: x + 0.18, y: 1.74, w: 0.9, h: 0.5,
      fontSize: 26, fontFace: FONT.latin, color: COLOR.accent, bold: true,
      align: 'left', valign: 'middle', inset: 0,
    }, 'fg', `rm-idx-${i}`)
    pl.text(w.what, {
      x: x + 0.18, y: 2.3, w: cardW - 0.36, h: 0.66,
      fontSize: 14, fontFace: FONT.sans, color: COLOR.ink, bold: true,
      align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.2,
    }, 'fg', `rm-what-${i}`)
    pl.text([
      { text: '里程碑', options: { color: COLOR.muted, fontSize: 9.5, bold: true } },
      { text: '\n' + (w.milestone ?? '—'), options: { color: COLOR.accent, fontSize: 12, bold: true } },
    ], {
      x: x + 0.18, y: 3.0, w: cardW - 0.36, h: 0.66, fontSize: 12,   // opts.fontSize=设计字号（run 覆盖渲染，几何记录用）
      fontFace: FONT.sans, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.18,
    }, 'fg', `rm-milestone-${i}`)
    pl.text(`Owner：${w.owner ?? '—'}`, {
      x: x + 0.18, y: 3.78, w: cardW - 0.36, h: 0.3,
      fontSize: 11, fontFace: FONT.sans, color: COLOR.label,
      align: 'left', valign: 'middle', inset: 0.02,
    }, 'fg', `rm-owner-${i}`)
  })

  if (spec.linkNote) {
    pl.text(spec.linkNote, {
      x: 0.5, y: 4.48, w: 9.0, h: 0.3,
      fontSize: 10.5, fontFace: FONT.sans, color: COLOR.muted, italic: true,
      align: 'left', valign: 'middle', inset: 0.02,
    }, 'fg', 'rm-linknote')
  }
}
