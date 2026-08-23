// check-slides：结构 QA（构建后对几何模型 + 解析产物检查）
// 覆盖：页数/标题/文字密度/字号/折行裁切/元素重叠越界/占位符/notes/图表数字=facts
import { CANVAS, DENSITY_LIMIT } from '../components/tokens.mjs'
import { Placer, inCanvas } from '../components/placer.mjs'

const PLACEHOLDER_RE = /TODO|FIXME|xxx|占位|待补充|待填写|lorem|ipsum|\?\?\?/i
const MIN_FONT = 9        // 全 deck 字号下限（来源行）
const MIN_BODY_FONT = 10  // 正文字号下限

export function checkSlides(geometry, slidesResolved, facts, storyboard) {
  const errs = [], warns = []

  // 1. 页数一致
  if (geometry.length !== storyboard.slides.length) {
    errs.push(`页数不一致：几何 ${geometry.length} vs storyboard ${storyboard.slides.length}`)
  }

  geometry.forEach(page => {
    const tag = `slide ${page.no}`

    // 2. 标题元素存在且可读字号
    const titleEl = page.elements.find(e => e.name === 'title' || e.name === 'cover-title')
    if (!titleEl) errs.push(`${tag}: 缺标题元素`)
    else if ((titleEl.fontSize ?? 0) < 20) errs.push(`${tag}: 标题字号 ${titleEl.fontSize} < 20`)

    // 3. 字号纪律
    for (const el of page.elements) {
      if (el.kind === 'text') {
        if (el.fontSize < MIN_FONT) errs.push(`${tag}: 元素 ${el.name} 字号 ${el.fontSize} < ${MIN_FONT}`)
        else if (el.fontSize < MIN_BODY_FONT && el.name !== 'source' && el.name !== 'pageno' && !/kpi|cover-foot/.test(el.name)) {
          errs.push(`${tag}: 元素 ${el.name} 字号 ${el.fontSize} < ${MIN_BODY_FONT}`)
        }
      }
    }

    // 4. 越界
    for (const el of page.elements) {
      if (!inCanvas(el)) errs.push(`${tag}: 元素 ${el.name} 越出画布 (${el.x},${el.y},${el.w},${el.h})`)
    }

    // 5. 前景重叠（fg 两两；容差 0.03in² 交叠面积）
    const fg = page.elements.filter(e => e.layer === 'fg')
    for (let i = 0; i < fg.length; i++) {
      for (let j = i + 1; j < fg.length; j++) {
        const a = fg[i], b = fg[j]
        const ox = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)
        const oy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y)
        if (ox > 0.02 && oy > 0.02 && ox * oy > 0.03) {
          errs.push(`${tag}: 前景元素重叠 ${a.name} × ${b.name}（交叠 ${ox.toFixed(2)}×${oy.toFixed(2)}in）`)
        }
      }
    }

    // 6. 文字容量（折行估算 vs 框高）与密度
    let slideChars = 0
    for (const el of page.elements) {
      if (el.kind !== 'text' || !el.text) continue
      const cjkish = el.text.replace(/[\u0000-\u00ff]/g, '')
      slideChars += cjkish.length
      if (['source', 'pageno', 'tag'].includes(el.name)) continue
      const estH = Placer.estTextH(el.text, el.fontSize, el.w - 0.06)
      if (estH > el.h * 1.04) {
        errs.push(`${tag}: 元素 ${el.name} 文字超出框高（估 ${estH.toFixed(2)}in > 框 ${el.h.toFixed(2)}in，${el.text.length} 字）`)
      }
      if (cjkish.length > DENSITY_LIMIT.perBlock && !['title', 'cover-title', 'cover-subtitle'].includes(el.name)) {
        warns.push(`${tag}: 元素 ${el.name} 单块 ${cjkish.length} 字超密度上限 ${DENSITY_LIMIT.perBlock}`)
      }
    }
    if (slideChars > DENSITY_LIMIT.perSlide * 1.6) {
      warns.push(`${tag}: 全页中文字符 ${slideChars} 偏高（页面应为结论+证据，论证进 notes）`)
    }

    // 7. 占位符
    for (const el of page.elements) {
      if (el.kind === 'text' && PLACEHOLDER_RE.test(el.text)) {
        errs.push(`${tag}: 元素 ${el.name} 含未替换占位符「${PLACEHOLDER_RE.exec(el.text)[0]}」`)
      }
    }

    // 8. 图表数字 = facts（重新解析比对，防止绕过插值直改数据）
    for (const el of page.elements) {
      if (el.kind !== 'chart' || !el.chartMeta) continue
      const { data } = el.chartMeta
      for (const series of data) {
        for (const v of series.values) {
          if (typeof v !== 'number' || Number.isNaN(v)) errs.push(`${tag}: 图表 ${el.name} 含非数值 ${v}`)
        }
      }
    }
  })

  // 9. chart 数值与 facts 逐一比对（解析产物 vs facts 原值）
  slidesResolved.forEach(sl => {
    if (!sl.chart) return
    const check = (specVal, factRef) => {
      const [id, field] = factRef.split('.')
      const f = facts.map.get(id)
      const raw = field ? f?.[field]?.value ?? f?.[field] : f?.value
      if (Number(specVal) !== Number(raw)) {
        errs.push(`slide ${sl.no}: 图表数值 ${specVal} ≠ facts ${factRef}=${raw}`)
      }
    }
    if (sl.chart.type === 'metricsBar') {
      sl.chart.metrics.forEach(m => { check(m.baseline, m.baselineFact); check(m.current, m.currentFact) })
    } else {
      const refs = []
      sl.chart.series?.forEach(s => refs.push(...(s.factValues ?? [])))
      sl.chart.segments?.forEach(s => refs.push(...(s.factValues ?? [])))
      const vals = [...(sl.chart.series ?? []).map(s => s.values), ...(sl.chart.segments ?? []).map(s => s.values)].flat()
      refs.forEach((r, i) => check(vals[i], r))
    }
  })

  return { errs, warns }
}
