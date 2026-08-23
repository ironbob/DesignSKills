// check-storyboard：构建前置 gate（storyboard + facts 完整性/叙事规则/决策闭环/数字引用纪律）
// 纪律：slide 文本中的数字一律走 {{F-x}} 插值——裸数字（白名单除外）= ERROR，从源头防网页/PPT 数字漂移
import { LAYOUTS, PLAN_LAYOUTS } from '../layouts/index.mjs'

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
  for (const re of ALLOWED_BARE) s = s.replace(re, '‖')
  return [...s.matchAll(/(?<![\w.,-])\d[\d,]*(?:\.\d+)?(?![\w-])/g)].map(m => m[0])
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
    const hasEvidence = Boolean(sl.chart || sl.flow || sl.kpis?.length || sl.pairs?.length || sl.requests?.length)
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
  })

  // facts 完整性
  for (const f of facts.meta.facts ?? []) {
    if (!f.id || !f.label) errs.push(`facts: 条目缺 id/label`)
    if (!['measured', 'derived', 'draft'].includes(f.confidence)) errs.push(`facts ${f.id}: confidence 非法 ${f.confidence}`)
    if (!f.source) errs.push(`facts ${f.id}: source 缺失（数字必须可溯源）`)
  }
  return { errs, warns }
}
