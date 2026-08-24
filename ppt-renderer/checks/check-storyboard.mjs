// check-storyboard：构建前置 gate（storyboard + facts 完整性/叙事规则/决策闭环/数字引用纪律）
// 纪律：slide 文本中的数字一律走 {{F-x}} 插值——裸数字（白名单除外）= ERROR，从源头防网页/PPT 数字漂移
// 演讲可读性 gate（spec：docs/2026-08-24-ppt-readability-qa/spec.md）：内容预算 / 结论—证据一致性 / 版式语义
import { LAYOUTS, PLAN_LAYOUTS } from '../layouts/index.mjs'
import { BUDGET, TITLE_HARD_MAX, CAPS, HERO_KIND, budgetErrs, screenPoints, deriveHeroFactRefs } from '../layouts/budgets.mjs'
import { interpDeep } from '../builders/resolve.mjs'

const NEUTRAL_TITLE = /^(数据分[析]|项目进展|工作汇报|情况汇报|工作总结|阶段汇报|总结|概览|背景介绍|目录|附录)$/

// 裸数字白名单：年份/日期/尺寸/编号引用/H1H2/中文数字不构成数据漂移
const ALLOWED_BARE = [
  /\d{4}-\d{1,2}(-\d{1,2})?/,   // 完整日期先于年份/H1 规则吞掉
  /\d{4}\s*H[12]/,
  /\d{4}\s*[年.-]/, /\d{1,2}\s*月/, /\d{1,2}\s*日/, /[FDPGBT]-\d+/,
  /\d{2}\s*台账/, /\b16:9\b/, /\bH[12]\b/, /\b\d+x\b/,
]
function bareNumberHits(text) {
  let s = String(text)
  s = s.replace(/\{\{[^}]+\}\}/g, '‖')            // 插值引用不算裸数字
  for (const re of ALLOWED_BARE) s = s.replace(new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g"), "‖")
  return [...s.matchAll(/(?<![\w.,-])\d[\d,]*(?:\.\d+)?(?![\w-])/g)].map(m => m[0])
}

const cjk = s => [...String(s ?? "")].filter(ch => ch.charCodeAt(0) > 0xff).length

/** title 的插值引用（id 级；声明/推导/比对统一口径） */
const refsIn = s => [...new Set([...String(s ?? '').matchAll(/\{\{\s*([^}]+?)\s*\}\}/g)].map(m => m[1].split('.')[0]))]

/** 非数字结论软校验：title 去插值后的 CJK bigram 与主视觉标签文本的重叠率 */
function heroOverlapWarn(sl, tag, warns) {
  const titleCjk = (String(sl.title ?? '').replace(/\{\{[^}]+\}\}/g, ' ').match(/[一-鿿]+/g) ?? []).join('')
  const bigrams = [...titleCjk].map((c, i, a) => (a[i + 1] ? c + a[i + 1] : null)).filter(Boolean)
  if (bigrams.length < 2) return
  const heroText = heroLabelText(sl)
  if (!heroText) return
  const heroBigrams = new Set([...heroText].map((c, i, a) => (a[i + 1] ? c + a[i + 1] : null)).filter(Boolean))
  const hit = bigrams.filter(b => heroBigrams.has(b)).length
  if (hit / bigrams.length < 0.34) {
    warns.push(`${tag}: 标题与主视觉关键词重叠 ${(hit / bigrams.length).toFixed(2)} < 0.34（非数字结论建议自查是否由主视觉表达）`)
  }
}

/** 各版式主视觉的可见标签文本（关键词软校验用） */
function heroLabelText(sl) {
  switch (sl.layout) {
    case 'exec-summary': return (sl.kpis ?? []).map(k => k.label).join('')
    case 'conclusion-chart': {
      const c = sl.chart ?? {}
      return [...(c.metrics ?? []).map(m => m.label), ...(c.series ?? []).map(s => s.name), ...(c.segments ?? []).map(s => s.name), ...(c.catLabels ?? [])].join('')
    }
    case 'mechanism': return (sl.flow?.rows ?? []).flatMap(r => [r.label, ...(r.steps ?? []).map(s => s.label)]).join('')
    case 'risk-action': return (sl.pairs ?? []).map(p => p.risk?.what).join('')
    case 'decision-ask': return (sl.requests ?? []).map(r => r.what).join('')
    case 'roadmap': return (sl.workstreams ?? []).map(w => w.what).join('')
    default: return ''
  }
}

/** 版式语义 + 条数容量（超量 = ERROR；builder 不做 slice 静默截断，由此拦截） */
function semanticsErrs(sl, tag, resolved) {
  const errs = []
  if (sl.layout === 'exec-summary') {
    const fourModules = sl.thesis && (sl.risks?.length ?? 0) > 0 && (sl.kpis?.length ?? 0) > 0 && sl.ask
    if (fourModules && cjk(resolved?.thesis) > 48) {
      errs.push(`${tag}: 长 thesis（${cjk(resolved.thesis)} 字）与风险列表+四 KPI+ask 同屏——压缩 thesis 至 48 字内或拆页`)
    }
  }
  if (sl.layout === 'decision-ask' && (sl.requests?.length ?? 0) > 2) {
    errs.push(`${tag}: 请求 ${sl.requests.length} 项 > 2——最多两项请求，第三项移 roadmap/附录`)
  }
  if (sl.layout === 'roadmap') {
    if (sl.requests?.length || sl.askLine) errs.push(`${tag}: roadmap 不得承载 requests/askLine（资源申请属 decision-ask）`)
    const banned = (sl.workstreams ?? []).flatMap((w, i) =>
      ['target', 'baseline', 'resources'].filter(k => w?.[k]).map(k => `workstreams[${i}].${k}`))
    if (banned.length) errs.push(`${tag}: roadmap 不得承载资源申请字段 ${banned.join('、')}（属 decision-ask）`)
  }
  if (sl.layout === 'conclusion-chart' && (sl.takeaways?.length ?? 0) > 2) {
    errs.push(`${tag}: 辅助说明 ${sl.takeaways.length} 条 > 2——右栏最多两条，禁止长段落`)
  }
  const capChecks = [
    ['meta', sl.meta], ['kpis', sl.kpis], ['risks', sl.risks],
    ['flow.rows', sl.flow?.rows], ['pairs', sl.pairs], ['workstreams', sl.workstreams],
    ...((sl.flow?.rows ?? []).map((r, i) => [`flow.rows[${i}].steps`, r.steps])),
  ]
  for (const [name, arr] of capChecks) {
    const cap = name.endsWith('.steps') ? CAPS['flow.rows[].steps'] : CAPS[name]
    if (cap !== undefined && (arr?.length ?? 0) > cap) {
      errs.push(`${tag}: ${name} ${arr.length} 项超容量 ${cap}——不允许 builder 静默截断，请删减或拆页`)
    }
  }
  return errs
}

export function checkStoryboard(sb, facts) {
  const errs = [], warns = []
  if (!sb?.deck?.title) errs.push('deck.title 缺失')
  for (const k of ['audience', 'purpose', 'minutes', 'aspect']) {
    if (sb?.deck?.[k] === undefined) errs.push(`deck.${k} 缺失（阶段 5P 演讲情境未定义）`)
  }
  if (sb?.deck?.aspect !== '16:9') errs.push('deck.aspect 必须为 16:9')
  if (!Array.isArray(sb?.slides) || sb.slides.length === 0) errs.push('slides 为空')

  const seenNos = new Set()
  sb?.slides?.forEach((sl, i) => {
    const tag = `slide ${sl.no ?? i + 1}`
    if (sl.no !== undefined) {
      if (seenNos.has(sl.no)) errs.push(`${tag}: 页号重复`)
      seenNos.add(sl.no)
    }
    if (!LAYOUTS[sl.layout]) errs.push(`${tag}: 未知版式 ${sl.layout}`)
    if (!sl.title?.trim()) errs.push(`${tag}: 标题缺失`)

    // 叙事规则：标题即结论（title 版式豁免——deck 标题页）
    if (sl.layout !== 'title' && sl.title && NEUTRAL_TITLE.test(sl.title.trim())) {
      errs.push(`${tag}: 中性标题「${sl.title}」——每页标题必须是结论`)
    }

    // notes：演讲稿 + 来源
    if (!sl.notes?.talk || sl.notes.talk.length < 60) errs.push(`${tag}: notes.talk 缺失或 <60 字`)
    const hasEvidence = Boolean(sl.chart || sl.flow || sl.kpis?.length || sl.pairs?.length || sl.requests?.length || sl.workstreams?.length)
    if (hasEvidence && !(sl.notes?.sources?.length)) errs.push(`${tag}: 有证据件但 notes.sources 为空`)

    // 决策闭环：计划/决策页必须有 Owner/截止/目标/基线/资源/ask
    if (PLAN_LAYOUTS.has(sl.layout)) {
      if (sl.layout === 'decision-ask') {
        if (!sl.askLine?.trim()) errs.push(`${tag}: 缺「需要谁现在决定什么」askLine`)
        ;(sl.requests ?? []).forEach((r, ri) => {
          for (const k of ['what', 'target', 'baseline', 'resources', 'owner', 'deadline']) {
            if (!String(r[k] ?? '').trim()) errs.push(`${tag}: 请求${ri + 1} 缺 ${k}（决策闭环字段）`)
          }
        })
      } else {
        ;(sl.pairs ?? []).forEach((p, pi) => {
          for (const k of ['owner', 'deadline']) {
            if (!String(p.action?.[k] ?? '').trim()) errs.push(`${tag}: 行动${pi + 1} 缺 action.${k}`)
          }
        })
      }
    }

    // 数字纪律：文本字段禁裸数字
    const walk = (obj, pathStr) => {
      if (typeof obj === 'string') {
        const hits = bareNumberHits(obj)
        if (hits.length) errs.push(`${tag}: ${pathStr} 存在裸数字 ${JSON.stringify(hits)}——请改用 {{F-x}} 插值`)
      } else if (Array.isArray(obj)) obj.forEach((v, j) => walk(v, `${pathStr}[${j}]`))
      else if (obj && typeof obj === 'object') {
        for (const [k, v] of Object.entries(obj)) {
          if (k === 'talk' || k === 'sources' || k === 'gaps' || k === 'format') continue  // notes 口径转述与数字格式代码不属数据
          walk(v, `${pathStr}.${k}`)
        }
      }
    }
    walk(sl, 'slide')

    // 插值引用可解析
    const refWalk = obj => {
      if (typeof obj === 'string') {
        for (const m of obj.matchAll(/\{\{\s*([^}]+?)\s*\}\}/g)) {
          const [id] = m[1].split('.')
          if (!facts.map.has(id)) errs.push(`${tag}: 插值引用 ${m[1]} 在 facts 中不存在`)
        }
      } else if (Array.isArray(obj)) obj.forEach(refWalk)
      else if (obj && typeof obj === 'object') Object.values(obj).forEach(refWalk)
    }
    refWalk(sl)

    // ── 演讲可读性 gate（spec §1.1/§2.1/§2.2；超预算 = ERROR）──
    if (LAYOUTS[sl.layout] && BUDGET[sl.layout]) {
      let rsl = null
      try { rsl = interpDeep(sl, facts) } catch { /* 坏引用已由 refWalk 报错，本页预算跳过 */ }

      // 1. 内容预算：标题/正文/单块字数 + screenPoints（按解析后字数计）
      if (rsl) {
        errs.push(...budgetErrs(sl.layout, rsl, tag))
        const tc = cjk(rsl.title)
        if (tc > TITLE_HARD_MAX) errs.push(`${tag}: 标题 ${tc} 字超过两行容量 ${TITLE_HARD_MAX}`)
        else if (tc > BUDGET[sl.layout].titleChars) warns.push(`${tag}: 标题 ${tc} 字超一行建议 ${BUDGET[sl.layout].titleChars}（两行内可过，鼓励一行）`)
        const pts = screenPoints(rsl)
        if (pts > BUDGET[sl.layout].points) errs.push(`${tag}: 同屏信息点 ${pts} > ${BUDGET[sl.layout].points}（观众需逐个消化的单元超载）`)
      }

      // 2. 结论—证据一致性：标题关键事实必须由主视觉直接表达（标题讲A、主图讲B = ERROR）
      if (sl.layout !== 'title') {
        const declared = sl.heroEvidence
        if (declared && declared.kind !== HERO_KIND[sl.layout]) {
          errs.push(`${tag}: heroEvidence.kind '${declared.kind}' 与版式主视觉 '${HERO_KIND[sl.layout]}' 不符`)
        }
        const derived = deriveHeroFactRefs(sl)
        if (declared?.factRefs) {
          const dec = new Set(declared.factRefs.map(r => String(r).split('.')[0]))
          const der = new Set(derived)
          const extra = [...dec].filter(x => !der.has(x)), lack = [...der].filter(x => !dec.has(x))
          if (extra.length || lack.length) errs.push(`${tag}: heroEvidence.factRefs 与实际主视觉漂移（多 ${JSON.stringify(extra)} 少 ${JSON.stringify(lack)}）`)
        }
        const heroSet = new Set(declared?.factRefs ? declared.factRefs.map(r => String(r).split('.')[0]) : derived)
        const missing = refsIn(sl.title).filter(r => !heroSet.has(r))
        if (missing.length) errs.push(`${tag}: 标题关键事实 ${missing.join('、')} 未由主视觉直接表达（标题讲A、主图讲B）`)
        else heroOverlapWarn(sl, tag, warns)
      }

      // 3. 版式语义 + 条数容量（禁 builder 静默截断）
      errs.push(...semanticsErrs(sl, tag, rsl))
    }
  })

  // facts 完整性
  for (const f of facts.meta.facts ?? []) {
    if (!f.id || !f.label) errs.push(`facts: 条目缺 id/label`)
    if (!['measured', 'derived', 'draft'].includes(f.confidence)) errs.push(`facts ${f.id}: confidence 非法 ${f.confidence}`)
    if (!f.source) errs.push(`facts ${f.id}: source 缺失（数字必须可溯源）`)
  }
  return { errs, warns }
}
