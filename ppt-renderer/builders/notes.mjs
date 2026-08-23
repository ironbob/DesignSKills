// Speaker notes 组装：页面只放结论+必要证据；口径、来源、假设、演讲稿全进 notes
import { factPath } from './resolve.mjs'

export function buildNotes(slide, facts, deckMeta) {
  const lines = []
  lines.push('【演讲稿】')
  lines.push(slide.notes?.talk ?? `（讲 ${slide.title}）`)
  lines.push('')
  const refs = collectFactRefs(slide)
  if (refs.length) {
    lines.push('【口径与来源】')
    for (const r of refs) {
      const f = factPath(facts, r)
      const conf = f.confidence === 'measured' ? '实测' : f.confidence === 'derived' ? '推算（仅图示/派生，勿当素材值引用）' : f.confidence === 'draft' ? '起草（计划值，待人工复核）' : f.confidence
      lines.push(`- ${f.id} ${f.label}：${f.display}｜口径：${f.caliber}｜来源：${f.source}｜置信：${conf}`)
    }
    lines.push('')
  }
  if (slide.notes?.sources?.length) {
    lines.push('【其他来源】')
    lines.push(...slide.notes.sources.map(s => `- ${s}`))
    lines.push('')
  }
  if (slide.notes?.gaps?.length) {
    lines.push('【待核实】')
    lines.push(...slide.notes.gaps.map(g => `- ${g}`))
    lines.push('')
  }
  lines.push(`【deck】${deckMeta.audience} · ${deckMeta.minutes} 分钟 · 目的：${deckMeta.purpose}`)
  return lines.join('\n')
}

function collectFactRefs(slide) {
  const refs = new Set()
  const walk = obj => {
    if (typeof obj === 'string') {
      for (const m of obj.matchAll(/\{\{\s*([^}]+?)\s*\}\}/g)) {
        refs.add(m[1].replace(/\.(baseline|value)$/, '').trim())
      }
    } else if (Array.isArray(obj)) obj.forEach(walk)
    else if (obj && typeof obj === 'object') Object.values(obj).forEach(walk)
  }
  walk(slide)
  return [...refs]
}
