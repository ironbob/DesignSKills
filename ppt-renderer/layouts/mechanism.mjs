// 版式 4/7 · 机制/流程：双排原生形状流程 + 运行结果证据条
import { COLOR, FONT, TYPE } from '../components/tokens.mjs'
import { titleBlock, sourceFooter, panel, COMMON_FONT_SPEC } from '../components/chrome.mjs'
import { flowRows } from '../components/flow.mjs'

export const FONT_SPEC = {
  ...COMMON_FONT_SPEC,
  'flow-rowlabel': 10, 'flow-step': TYPE.step, 'flow-sub': TYPE.stepSub, 'flow-linknote': 10,
  'mech-evidence': 12.5,
}
export const HERO_NAMES = ['flow-step', 'flow-sub']
export const KEY_ELEMENTS = [{ prefix: 'flow-step', min: 12, bold: true }]

export function render({ pl, spec, pageNo, total }) {
  titleBlock(pl, { tag: spec.tag, title: spec.title })
  sourceFooter(pl, { source: spec.source, pageNo, total })

  flowRows(pl, spec.flow, { x: 0.5, y: 1.5, w: 9.0, h: 2.62 })

  // 运行结果证据条（机制的有效性证据，数字走 facts 插值）
  panel(pl, { x: 0.5, y: 4.42, w: 9.0, h: 0.48, fill: COLOR.panel })
  pl.text([
    { text: '运行结果　', options: { color: COLOR.muted, fontSize: 11, bold: true } },
    { text: spec.evidence, options: { color: COLOR.label, fontSize: 12.5 } },
  ], {
    x: 0.66, y: 4.44, w: 8.7, h: 0.44, fontSize: 12.5,   // opts.fontSize=设计字号（run 覆盖渲染，几何记录用）
    fontFace: FONT.sans, align: 'left', valign: 'middle', inset: 0.02,
  }, 'fg', 'mech-evidence')
}
