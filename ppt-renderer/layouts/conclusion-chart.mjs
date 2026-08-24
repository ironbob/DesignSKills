// 版式 3/7 · 结论 + 数据图：左原生图表，右证据要点栏
// 版式语义：右栏最多两条辅助说明（takeaways ≤2，禁长段落，gate 1 拦截）
import { COLOR, FONT } from '../components/tokens.mjs'
import { titleBlock, sourceFooter, COMMON_FONT_SPEC } from '../components/chrome.mjs'
import { renderChart } from '../components/chart.mjs'

export const FONT_SPEC = { ...COMMON_FONT_SPEC, 'cc-takeaway': 12.5, 'chart-metric-label': 10.5 }
export const HERO_NAMES = ['chart-metric', 'chart-grouped', 'chart-stacked']
export const KEY_ELEMENTS = []   // 图表类主视觉由 hero 占比 gate 把守，无文本关键元素

export function render({ pl, pres, spec, pageNo, total }) {
  titleBlock(pl, { tag: spec.tag, title: spec.title })
  sourceFooter(pl, { source: spec.source, pageNo, total })

  renderChart(pl, pres, spec.chart, { x: 0.5, y: 1.5, w: 5.85, h: 3.3 })

  // 右栏证据要点（结论的支撑链，细节口径进 notes；≤2 条由 gate 1 拦截超量）
  const railX = 6.6, railW = 2.9
  let y = 1.58
  spec.takeaways.forEach((tk, i) => {
    pl.text([
      { text: '▪ ', options: { color: COLOR.accent, fontSize: 13, bold: true } },
      { text: tk, options: { color: COLOR.label, fontSize: 12.5 } },
    ], {
      x: railX, y, w: railW, h: 0.92, fontSize: 12.5,   // opts.fontSize=设计字号（run 覆盖渲染，几何记录用）
      fontFace: FONT.sans, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.24,
    }, 'fg', `cc-takeaway-${i}`)
    y += 1.04
  })
}
