// 版式 1/6 · 标题页：deck 标题 + 结论式副标 + 汇报情境行
import { COLOR, FONT, TYPE, GRID } from '../components/tokens.mjs'

export function render({ pl, spec }) {
  pl.shape(pl.slide, 'rect', {
    x: 0.9, y: 1.38, w: 1.1, h: 0.04,
    fill: { color: COLOR.accent }, line: { type: 'none' },
  }, 'bg', 'cover-rule')
  pl.text(spec.title, {
    x: 0.9, y: 1.58, w: 8.3, h: 0.85,
    fontSize: TYPE.coverTitle, fontFace: FONT.sans, color: COLOR.ink, bold: true,
    align: 'left', valign: 'top', inset: 0,
  }, 'fg', 'cover-title')
  pl.text(spec.subtitle, {
    x: 0.9, y: 2.62, w: 8.3, h: 0.72,
    fontSize: TYPE.coverSub, fontFace: FONT.sans, color: COLOR.label,
    align: 'left', valign: 'top', inset: 0, lineSpacingMultiple: 1.3,
  }, 'fg', 'cover-subtitle')
  pl.text(spec.meta.join('　｜　'), {
    x: 0.9, y: 3.82, w: 8.3, h: 0.52,
    fontSize: 12, fontFace: FONT.sans, color: COLOR.muted,
    align: 'left', valign: 'top', inset: 0, lineSpacingMultiple: 1.3,
  }, 'fg', 'cover-meta')
  pl.text(spec.footNote ?? '内部资料 · 请勿外传', {
    x: 0.9, y: GRID.srcY, w: 6, h: GRID.srcH,
    fontSize: TYPE.source, fontFace: FONT.sans, color: COLOR.muted,
    align: 'left', valign: 'middle', inset: 0,
  }, 'fg', 'cover-foot')
}
