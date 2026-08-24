// 版式 6/7 · 决策请求/资源申请：请求卡（目标/基线/资源/Owner/截止）+ 需要谁现在决定什么
// 版式语义：最多两项请求（gate 1 拦截 >2）——第三项移 roadmap/附录；不设紧凑三卡模式（投屏可读性红线）
import { COLOR, FONT } from '../components/tokens.mjs'
import { titleBlock, sourceFooter, panel, COMMON_FONT_SPEC } from '../components/chrome.mjs'

const FIELDS = [
  { key: 'target', label: '目标（vs 基线）', merge: 'baseline' },
  { key: 'resources', label: '资源需求' },
  { key: 'owner', label: 'Owner' },
  { key: 'deadline', label: '截止时间' },
]

export const FONT_SPEC = {
  ...COMMON_FONT_SPEC,
  'da-what': 14, 'da-target': 11, 'da-resources': 11, 'da-owner': 11, 'da-deadline': 11, 'da-ask': 13,
}
export const HERO_NAMES = ['da-what', 'da-target', 'da-resources', 'da-owner', 'da-deadline']
export const KEY_ELEMENTS = [{ prefix: 'da-what', min: 12, bold: true }, { prefix: 'da-ask', min: 12, bold: true }]

export function render({ pl, spec, pageNo, total }) {
  titleBlock(pl, { tag: spec.tag ?? '决策请求', title: spec.title })
  sourceFooter(pl, { source: spec.source, pageNo, total })

  spec.requests.forEach((r, i) => {
    const y = 1.44 + i * 1.58
    panel(pl, { x: 0.5, y, w: 9.0, h: 1.48, fill: COLOR.panel })
    pl.text(`请求 ${i + 1}　${r.what}`, {
      x: 0.68, y: y + 0.08, w: 8.64, h: 0.32,
      fontSize: 14, fontFace: FONT.sans, color: COLOR.ink, bold: true, align: 'left', valign: 'middle', inset: 0.02,
    }, 'fg', `da-what-${i}`)
    FIELDS.forEach((f, fi) => {
      const fx = 0.68 + fi * 2.22
      let value = r[f.key] ?? '—'
      if (f.merge && r[f.merge]) value = `${value}（基线：${r[f.merge]}）`
      pl.text([
        { text: f.label, options: { color: COLOR.muted, fontSize: 9.5, bold: true } },
        { text: '\n' + value, options: { color: COLOR.label, fontSize: 11 } },
      ], {
        x: fx, y: y + 0.5, w: 2.1, h: 0.88, fontSize: 11,   // opts.fontSize=设计字号（run 覆盖渲染，几何记录用）
        fontFace: FONT.sans, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.18,
      }, 'fg', `da-${f.key}-${i}`)
    })
  })

  pl.shape(pl.slide, 'rect', {
    x: 0.5, y: 4.66, w: 9.0, h: 0.4,
    fill: { color: COLOR.accent }, line: { type: 'none' },
  }, 'bg', 'da-askband')
  pl.text(`需要您现在决定：${spec.askLine}`, {
    x: 0.68, y: 4.66, w: 8.64, h: 0.4,
    fontSize: 13, fontFace: FONT.sans, color: 'FFFFFF', bold: true,
    align: 'left', valign: 'middle', inset: 0.02,
  }, 'fg', 'da-ask')
}
