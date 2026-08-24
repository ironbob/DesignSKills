// 演讲可读性预算契约（spec：docs/2026-08-24-ppt-readability-qa/spec.md §2.1/§2.2）
// 字数 = 解析插值后的中文字符；source footer / notes / tag / 页码不计入正文预算
// 超预算一律 ERROR（防文字墙；论证进 notes）。阈值来源：各文本框几何容量 ×80% 反推。
export const TITLE_HARD_MAX = 52   // 标题两行容量（23pt × 9.0in ≈ 28 字/行）；超过 = ERROR

/** 各版式主视觉类型（heroEvidence.kind 的合法值） */
export const HERO_KIND = {
  'title': 'none',
  'exec-summary': 'kpi',
  'conclusion-chart': 'chart',
  'mechanism': 'flow',
  'risk-action': 'pairs',
  'decision-ask': 'requests',
  'roadmap': 'roadmap',
}

export const BUDGET = {
  'title': {
    titleChars: 24, slideChars: 130, points: 4, whitespaceMin: 0.15,
    blockLimits: { subtitle: 42, 'meta[]': 28 },
  },
  'exec-summary': {
    titleChars: 30, slideChars: 260, points: 8, whitespaceMin: 0.15,
    blockLimits: { thesis: 48, 'risks[]': 30, ask: 36, 'kpis[].label': 12 },
  },
  'conclusion-chart': {
    titleChars: 30, slideChars: 180, points: 3, whitespaceMin: 0.15,
    blockLimits: { 'takeaways[]': 60 },
  },
  'mechanism': {
    titleChars: 30, slideChars: 190, points: 11, whitespaceMin: 0.15,
    blockLimits: { evidence: 45, 'flow.linkNote': 30, 'flow.rows[].label': 12, 'flow.rows[].steps[].label': 10, 'flow.rows[].steps[].sub': 14 },
  },
  'risk-action': {
    titleChars: 30, slideChars: 220, points: 4, whitespaceMin: 0.15,
    blockLimits: { 'pairs[].risk.what': 20, 'pairs[].risk.evidence': 55, 'pairs[].action.what': 20, 'pairs[].action.detail': 40, 'pairs[].action.owner': 16, 'pairs[].action.deadline': 24 },
  },
  'decision-ask': {
    titleChars: 30, slideChars: 240, points: 3, whitespaceMin: 0.03,   // 卡片版式：卡面板即内容，留白下限低
    blockLimits: { askLine: 44, 'requests[].what': 28, 'requests[].target': 32, 'requests[].baseline': 32, 'requests[].resources': 28, 'requests[].owner': 16, 'requests[].deadline': 24 },
  },
  'roadmap': {
    titleChars: 30, slideChars: 200, points: 3, whitespaceMin: 0.03,
    blockLimits: { linkNote: 30, 'workstreams[].what': 24, 'workstreams[].milestone': 28, 'workstreams[].owner': 16 },
  },
}

/** 条数上限（超 = ERROR；builder 不做 slice 静默截断，由 gate 1 拦截） */
export const CAPS = {
  meta: 3, kpis: 4, risks: 2, takeaways: 2,
  'flow.rows': 3, 'flow.rows[].steps': 4, pairs: 2, requests: 2, workstreams: 3,
}

/** 每版式的正文内容字段 walker（raw slide → [{path, text}]；不含 title/source/notes/tag） */
const CONTENT_FIELDS = {
  'title': sl => [
    { path: 'subtitle', text: sl.subtitle },
    ...(sl.meta ?? []).map((t, i) => ({ path: `meta[${i}]`, text: t })),
  ],
  'exec-summary': sl => [
    { path: 'thesis', text: sl.thesis },
    ...(sl.risks ?? []).map((t, i) => ({ path: `risks[${i}]`, text: t })),
    { path: 'ask', text: sl.ask },
    ...(sl.kpis ?? []).map((k, i) => ({ path: `kpis[${i}].label`, text: k.label })),
  ],
  'conclusion-chart': sl => [
    ...(sl.takeaways ?? []).map((t, i) => ({ path: `takeaways[${i}]`, text: t })),
  ],
  'mechanism': sl => [
    { path: 'evidence', text: sl.evidence },
    { path: 'flow.linkNote', text: sl.flow?.linkNote },
    ...(sl.flow?.rows ?? []).flatMap((row, ri) => [
      { path: `flow.rows[${ri}].label`, text: row.label },
      ...(row.steps ?? []).flatMap((st, si) => [
        { path: `flow.rows[${ri}].steps[${si}].label`, text: st.label },
        { path: `flow.rows[${ri}].steps[${si}].sub`, text: st.sub },
      ]),
    ]),
  ],
  'risk-action': sl => [
    ...(sl.pairs ?? []).flatMap((p, i) => [
      { path: `pairs[${i}].risk.what`, text: p.risk?.what },
      { path: `pairs[${i}].risk.evidence`, text: p.risk?.evidence },
      { path: `pairs[${i}].action.what`, text: p.action?.what },
      { path: `pairs[${i}].action.owner`, text: p.action?.owner },
      { path: `pairs[${i}].action.deadline`, text: p.action?.deadline },
      { path: `pairs[${i}].action.detail`, text: p.action?.detail },
    ]),
  ],
  'decision-ask': sl => [
    { path: 'askLine', text: sl.askLine },
    ...(sl.requests ?? []).flatMap((r, i) => [
      { path: `requests[${i}].what`, text: r.what },
      { path: `requests[${i}].target`, text: r.target },
      { path: `requests[${i}].baseline`, text: r.baseline },
      { path: `requests[${i}].resources`, text: r.resources },
      { path: `requests[${i}].owner`, text: r.owner },
      { path: `requests[${i}].deadline`, text: r.deadline },
    ]),
  ],
  'roadmap': sl => [
    { path: 'linkNote', text: sl.linkNote },
    ...(sl.workstreams ?? []).flatMap((w, i) => [
      { path: `workstreams[${i}].what`, text: w.what },
      { path: `workstreams[${i}].milestone`, text: w.milestone },
      { path: `workstreams[${i}].owner`, text: w.owner },
    ]),
  ],
}

const cjk = s => String(s ?? "").replace(/[\u0000-\u00ff]/g, "").length

/** path 'risks[1]' → 模式 'risks[]'，用于 blockLimits 匹配 */
function patternOf(path) {
  return path.replace(/\[\d+\]/g, '[]')
}

/** 内容预算检查（对已解析 slide）；返回 errs */
export function budgetErrs(layout, resolved, tag) {
  const b = BUDGET[layout]
  if (!b) return []
  const errs = []
  for (const { path, text } of CONTENT_FIELDS[layout](resolved) ?? []) {
    if (!text) continue
    const limit = b.blockLimits[patternOf(path)]
    if (limit !== undefined && cjk(text) > limit) {
      errs.push(`${tag}: ${path} 单块 ${cjk(text)} 字超上限 ${limit}（右栏/卡片禁长段落，细节进 notes）`)
    }
  }
  const bodyChars = (CONTENT_FIELDS[layout](resolved) ?? [])
    .reduce((s, f) => s + (f.text ? cjk(f.text) : 0), 0)
  if (bodyChars > b.slideChars) {
    errs.push(`${tag}: 正文屏幕字数 ${bodyChars} 超预算 ${b.slideChars}——页面只放结论+证据，论证进 notes`)
  }
  return errs
}

/** 同屏信息点 = 观众需逐个消化的语义单元（spec §4） */
export function screenPoints(sl) {
  switch (sl.layout) {
    case 'title': return 1 + (sl.meta?.length ?? 0)
    case 'exec-summary': return 1 + (sl.risks?.length ?? 0) + 1 + (sl.kpis?.length ?? 0)
    case 'conclusion-chart': return 1 + (sl.takeaways?.length ?? 0)
    case 'mechanism': return (sl.flow?.rows ?? []).reduce((s, r) => s + (r.steps?.length ?? 0), 0) + 1
    case 'risk-action': return (sl.pairs?.length ?? 0) * 2
    case 'decision-ask': return (sl.requests?.length ?? 0) + 1
    case 'roadmap': return sl.workstreams?.length ?? 0
    default: return 0
  }
}

const refsIn = s => [...String(s ?? '').matchAll(/\{\{\s*([^}]+?)\s*\}\}/g)].map(m => m[1].split('.')[0])
const refIds = arr => [...new Set((arr ?? []).flat())]

/** 从版式字段推导主视觉 factRefs（id 级；spec §1.1 表） */
export function deriveHeroFactRefs(sl) {
  switch (sl.layout) {
    case 'exec-summary': return refIds((sl.kpis ?? []).map(k => refsIn(k.value)))
    case 'conclusion-chart': {
      const c = sl.chart ?? {}
      const refs = [
        ...(c.metrics ?? []).flatMap(m => [m.baselineFact, m.currentFact]),
        ...(c.series ?? []).flatMap(s => s.factValues ?? []),
        ...(c.segments ?? []).flatMap(s => s.factValues ?? []),
      ].filter(Boolean).map(r => r.split('.')[0])
      return [...new Set(refs)]
    }
    case 'mechanism': return refIds([
      refsIn(sl.evidence),
      ...(sl.flow?.rows ?? []).flatMap(r => [
        refsIn(r.label),
        ...(r.steps ?? []).flatMap(st => [refsIn(st.label), refsIn(st.sub)]),
      ]),
    ])
    case 'risk-action': return refIds((sl.pairs ?? []).map(p => refsIn(p.risk?.evidence)))
    case 'decision-ask': return refIds((sl.requests ?? []).flatMap(r => [refsIn(r.target), refsIn(r.baseline)]))
    case 'roadmap': return refIds((sl.workstreams ?? []).map(w => refsIn(w.milestone)))
    default: return []
  }
}
