// deck 构建主循环：storyboard(已解析) → 每页一个版式 → 记录几何 → 组 notes
import PptxGenJS from 'pptxgenjs'
import { Placer } from '../components/placer.mjs'
import { CANVAS } from '../components/tokens.mjs'
import { LAYOUTS } from '../layouts/index.mjs'
import { interpDeep, resolveChart } from './resolve.mjs'
import { buildNotes } from './notes.mjs'

export async function buildDeck({ storyboard, facts, templateReport }) {
  const pres = new PptxGenJS()
  pres.defineLayout({ name: 'W169', width: CANVAS.W, height: CANVAS.H })
  pres.layout = 'W169'
  pres.title = storyboard.deck.title
  pres.author = storyboard.deck.presenter ?? 'expert-doc-writer'
  pres.company = storyboard.deck.company ?? ''

  const total = storyboard.slides.length
  const geometry = []       // 每页的元素几何（check-slides 输入）
  const slidesResolved = []

  storyboard.slides.forEach((rawSlide, idx) => {
    const slide = interpDeep(rawSlide, facts)
    if (slide.chart) slide.chart = resolveChart(slide.chart, facts)
    slidesResolved.push(slide)

    const s = pres.addSlide()
    const pl = new Placer(s)
    const layout = LAYOUTS[slide.layout]
    if (!layout) throw new Error(`未知版式 ${slide.layout}（可用：${Object.keys(LAYOUTS).join(', ')}）`)
    layout.render({
      pres, slide: s, pl, spec: slide, deck: storyboard.deck,
      pageNo: idx + 1, total, facts,
    })
    s.addNotes(buildNotes(rawSlide, facts, storyboard.deck))
    geometry.push({ no: slide.no ?? idx + 1, layout: slide.layout, title: slide.title, elements: pl.elements })
  })

  const file = await pres.writeFile({ fileName: 'deck.pptx' })
  return { pres, file, geometry, slidesResolved, templateReport }
}
