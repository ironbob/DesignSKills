// 解析层：facts.json 是唯一数字源。storyboard 里的数字一律以 {{F-x}} / {{F-x.baseline}} 插值，
// charts 的数值一律以 fact/factValues 引用——禁止两端各自维护数字。
export function loadFacts(raw) {
  const map = new Map()
  for (const f of raw.facts) map.set(f.id, f)
  return { meta: raw, map }
}

/** 'F-9' → fact；'F-9.baseline' → 子对象合并；'F-8.deltaDisplay' → 字符串/数值字段包装为 value+display */
export function factPath(facts, path) {
  const [id, field] = path.split('.')
  const f = facts.map.get(id)
  if (!f) throw new Error(`facts 中不存在 ${id}`)
  if (!field) return f
  const sub = f[field]
  if (sub === undefined) throw new Error(`fact ${id} 没有 ${field} 字段`)
  if (sub && typeof sub === 'object') return { ...f, ...sub }
  return { ...f, value: sub, display: String(sub) }
}

/** 插值：{{F-8}} → display；{{F-9.baseline}} → 基期 display；{{F-8.value}} → 原数值 */
export function interp(str, facts) {
  if (typeof str !== 'string') return str
  return str.replace(/\{\{([^}]+)\}\}/g, (_, path) => {
    const f = factPath(facts, path.trim())
    return path.trim().endsWith('.value') ? String(f.value) : f.display
  })
}

/** 深度遍历对象，插值所有字符串字段 */
export function interpDeep(obj, facts) {
  if (typeof obj === 'string') return interp(obj, facts)
  if (Array.isArray(obj)) return obj.map(v => interpDeep(v, facts))
  if (obj && typeof obj === 'object') {
    const out = {}
    for (const [k, v] of Object.entries(obj)) out[k] = interpDeep(v, facts)
    return out
  }
  return obj
}

/** chart spec 解析：fact 引用 → 数值。同时保留 display 供 QA 比对 */
export function resolveChart(chart, facts) {
  const c = structuredClone(chart)
  if (c.type === 'metricsBar') {
    c.metrics = c.metrics.map(m => {
      const base = factPath(facts, m.baselineFact)
      const cur = factPath(facts, m.currentFact)
      return {
        ...m,
        baseline: base.value, baselineDisplay: base.display,
        current: cur.value, currentDisplay: cur.display,
      }
    })
  } else if (c.type === 'groupedBar') {
    c.series = c.series.map(s => ({
      ...s,
      values: s.factValues.map(p => factPath(facts, p).value),
      displays: s.factValues.map(p => factPath(facts, p).display),
    }))
  } else if (c.type === 'stackedHBar') {
    c.segments = c.segments.map(sg => ({
      ...sg,
      values: sg.factValues.map(p => factPath(facts, p).value),
      displays: sg.factValues.map(p => factPath(facts, p).display),
    }))
  } else {
    throw new Error(`未知 chart.type: ${c.type}`)
  }
  return c
}
