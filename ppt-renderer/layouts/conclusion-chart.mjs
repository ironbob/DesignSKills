// 版式 3/6 · 结论 + 数据图：左原生图表，右证据要点栏
import { COLOR, FONT } from '../components/tokens.mjs'
import { titleBlock, sourceFooter } from '../components/chrome.mjs'
import { renderChart } from '../components/chart.mjs'

export function render({ pl, pres, spec, pageNo, total }) {
  titleBlock(pl, { tag: spec.tag, title: spec.title })
  sourceFooter(pl, { source: spec.source, pageNo, total })

  renderChart(pl, pres, spec.chart, { x: 0.5, y: 1.5, w: 5.85, h: 3.3 })

  // 右栏证据要点（结论的支撑链，细节口径进 notes）
  const railX = 6.6, railW = 2.9
  let y = 1.58
  spec.takeaways.forEach((tk, i) => {
    pl.text([
      { text: '▪ ', options: { color: COLOR.accent, fontSize: 13, bold: true } },
      { text: tk, options: { color: COLOR.label, fontSize: 12.5 } },
    ], {
      x: railX, y, w: railW, h: 0.92,
      fontFace: FONT.sans, align: 'left', valign: 'top', inset: 0.02, lineSpacingMultiple: 1.24,
    }, 'fg', `cc-takeaway-${i}`)
    y += 1.04
  })
}
