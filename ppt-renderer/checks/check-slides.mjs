// check-slides：结构 QA（构建后对几何模型 + 解析产物检查）
// 覆盖：页数/标题/文字容量/字号/折行裁切/元素重叠越界/占位符/notes/图表数字=facts
//       + 投屏可读性（spec §2.3：标题≤2行/反shrink/主视觉占比/文字面积/留白/卡片数/缩略图关键元素）
import { CANVAS, GRID, MARGIN, LINE_H } from '../components/tokens.mjs'
import { Placer, inCanvas } from '../components/placer.mjs'
import { LAYOUTS } from '../layouts/index.mjs'
import { BUDGET } from '../layouts/budgets.mjs'

const PLACEHOLDER_RE = /TODO|FIXME|xxx|占位|待补充|待填写|lorem|ipsum|\?\?\?/i
const MIN_FONT = 9        // 全 deck 字号下限（来源行）
const MIN_BODY_FONT = 10  // 正文字号下限

/** 矩形并集面积（0.05in 栅格；越界部分裁到正文区） */
function unionArea(rects, body) {
  const STEP = 0.05
  const cols = Math.ceil(body.w / STEP), rows = Math.ceil(body.h / STEP)
  const grid = new Uint8Array(cols * rows)
  for (const r of rects) {
    if (!r) continue
    const x0 = Math.max(0, Math.floor((r.x - body.x) / STEP))
    const y0 = Math.max(0, Math.floor((r.y - body.y) / STEP))
    const x1 = Math.min(cols, Math.ceil((r.x + r.w - body.x) / STEP))
    const y1 = Math.min(rows, Math.ceil((r.y + r.h - body.y) / STEP))
    for (let gy = y0; gy < y1; gy++) for (let gx = x0; gx < x1; gx++) grid[gy * cols + gx] = 1
  }
  let n = 0
  for (let i = 0; i < grid.length; i++) n += grid[i]
  return n * STEP * STEP
}

/** 文字 ink：面积（折行高 × 平均行宽填充）+ 占位矩形（留白并集用）；run 混排用加权字号 */
function textInk(el) {
  const size = el.wrapSize ?? el.fontSize
  const lines = Placer.estLines(el.text, size, el.w - 0.06)
  const h = Math.min((lines * size * LINE_H) / 72, el.h)
  const avgLineW = Placer.estTextW(el.text, size) / 72 / Math.max(lines, 1)
  const fill = Math.min(1, avgLineW / Math.max(el.w, 0.01))
  return { area: h * el.w * fill, box: { x: el.x, y: el.y, w: el.w, h } }
}

/** 名称匹配（严）：全等或「前缀-数字」边界——FONT_SPEC/KEY_ELEMENTS 用（ra-risk-0 ✓ / ra-risk-ev-0 ✗） */
const matchName = (name, key) =>
  name === key || new RegExp('^' + key.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '-\\d').test(name)

/** 名称匹配（宽）：前缀即命中——HERO_NAMES 用（ra-risk-ev-0 也属 ra-risk 主视觉卡） */
const matchLoose = (name, key) => name === key || name.startsWith(key)

/** 投屏可读性检查（spec §2.3） */
function checkProjection(page, errs, warns) {
  const tag = `slide ${page.no}`
  const layout = LAYOUTS[page.layout]
  if (!layout) return
  const body = { x: MARGIN.left, y: GRID.bodyY, w: CANVAS.W - MARGIN.left - MARGIN.right, h: GRID.bodyH }
  const bodyArea = body.w * body.h
  const headerNames = ['title', 'cover-title', 'source', 'pageno', 'tag', 'cover-foot']

  // 1. 标题 ≤ 2 行
  const titleEl = page.elements.find(e => e.name === 'title' || e.name === 'cover-title')
  if (titleEl && Placer.estLines(titleEl.text, titleEl.fontSize, titleEl.w) > 2) {
    errs.push(`${tag}: 标题超两行——投屏三秒读出结论的前提`)
  }

  // 2. 反 shrink-to-fit：渲染字号必须等于版式设计字号（±0.5pt 容差）
  const spec = layout.FONT_SPEC ?? {}
  const specKeys = Object.keys(spec).sort((a, b) => b.length - a.length)
  for (const el of page.elements) {
    if (el.kind !== 'text') continue
    const key = specKeys.find(k => matchName(el.name, k))
    if (key === undefined) continue
    if (el.fontSize < spec[key] - 0.5) {
      errs.push(`${tag}: 元素 ${el.name} 渲染字号 ${el.fontSize} < 设计 ${spec[key]}（shrink-to-fit 禁令）`)
    }
  }

  // 3. 主视觉占比 ≥ 35%
  const heroNames = layout.HERO_NAMES ?? []
  if (heroNames.length) {
    const heroRects = page.elements
      .filter(e => heroNames.some(p => matchLoose(e.name, p)))
      .map(e => ({ x: e.x, y: e.y, w: e.w, h: e.h }))
    const ratio = unionArea(heroRects, body) / bodyArea
    if (ratio < 0.35) errs.push(`${tag}: 主视觉占比 ${(ratio * 100).toFixed(0)}% < 35%（关键结论/数字须在缩略图可辨）`)
  }

  // 4. 文字面积占比（文字墙）与留白
  const contentRects = []
  let inkArea = 0
  for (const el of page.elements) {
    if (el.kind === 'text' && !headerNames.includes(el.name) && el.text) {
      const ink = textInk(el)
      inkArea += ink.area
      contentRects.push(ink.box)
    } else if (el.kind === 'chart' || (el.kind === 'shape' && (el.name === 'panel' || el.name === 'flow-node'))) {
      contentRects.push({ x: el.x, y: el.y, w: el.w, h: el.h })
    }
  }
  const inkRatio = inkArea / bodyArea
  if (inkRatio > 0.45) errs.push(`${tag}: 正文文字面积 ${(inkRatio * 100).toFixed(0)}% > 45%（文字墙——删文字进 notes）`)
  else if (inkRatio > 0.40) warns.push(`${tag}: 正文文字面积 ${(inkRatio * 100).toFixed(0)}% 偏高`)
  const wsMin = BUDGET[page.layout]?.whitespaceMin ?? 0.15
  const covered = unionArea(contentRects, body) / bodyArea
  if (1 - covered < wsMin) errs.push(`${tag}: 留白 ${((1 - covered) * 100).toFixed(0)}% < 下限 ${(wsMin * 100).toFixed(0)}%（内容塞满正文区）`)

  // 5. 卡片数量 ≤ 6（dashboard 式堆砌防线；flow-node 不计卡）
  const cards = page.elements.filter(e => e.kind === 'shape' && e.name === 'panel').length
  if (cards > 6) errs.push(`${tag}: 卡片 ${cards} > 6——一页一个主结论，不做卡片堆砌`)

  // 6. 缩略图关键元素：字号/加粗下限（结论、数字、请求在缩略图仍可识别）
  for (const ke of layout.KEY_ELEMENTS ?? []) {
    for (const el of page.elements) {
      if (el.kind !== 'text' || !matchName(el.name, ke.prefix)) continue
      if (el.fontSize < ke.min || (ke.bold && !el.bold)) {
        errs.push(`${tag}: 关键元素 ${el.name} 缩略图不可识别（字号 ${el.fontSize}${ke.bold ? '，需加粗' : ''}）`)
      }
    }
  }
}

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

    // 6. 文字容量（折行估算 vs 框高，run 混排用加权字号）；密度预算已前移 check-storyboard（按版式 ERROR，spec §2.1）
    for (const el of page.elements) {
      if (el.kind !== 'text' || !el.text) continue
      if (['source', 'pageno', 'tag'].includes(el.name)) continue
      const estH = Placer.estTextH(el.text, el.wrapSize ?? el.fontSize, el.w - 0.06)
      if (estH > el.h * 1.04) {
        errs.push(`${tag}: 元素 ${el.name} 文字超出框高（估 ${estH.toFixed(2)}in > 框 ${el.h.toFixed(2)}in，${el.text.length} 字）`)
      }
    }

    // 6b. 投屏可读性（spec §2.3：标题≤2行/反shrink/主视觉占比/文字面积/留白/卡片数/缩略图关键元素）
    checkProjection(page, errs, warns)

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
