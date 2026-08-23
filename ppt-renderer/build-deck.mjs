#!/usr/bin/env node
// build-deck.mjs —— ppt-renderer CLI
// 用法：
//   node build-deck.mjs --facts <facts.json> --storyboard <storyboard.json> --out <dir> \
//        [--template <user.pptx>] [--no-pdf] [--qa-only]
// 产出：<out>/<slug>.pptx、<out>/<slug>.pdf、<out>/png/slide-*.png、<out>/qa-report.{json,md}
import { readFileSync, writeFileSync, mkdirSync, existsSync, renameSync } from 'node:fs'
import { parseArgs } from 'node:util'
import { loadFacts } from './builders/resolve.mjs'
import { applyThemeOverrides } from './builders/theme.mjs'
import { buildDeck } from './builders/deck.mjs'
import { checkStoryboard } from './checks/check-storyboard.mjs'
import { checkSlides } from './checks/check-slides.mjs'
import { exportPdf, renderPngs, pdfTextCheck, edgeBleedCheck } from './checks/render-png.mjs'
import { writeQaReport } from './checks/qa.mjs'

const args = parseArgs({
  options: {
    facts: { type: 'string' }, storyboard: { type: 'string' }, out: { type: 'string' },
    template: { type: 'string' }, 'no-pdf': { type: 'boolean' }, 'qa-only': { type: 'boolean' },
  },
}).values

if (!args.facts || !args.storyboard || !args.out) {
  console.error('用法: node build-deck.mjs --facts <f.json> --storyboard <sb.json> --out <dir> [--template <t.pptx>]')
  process.exit(2)
}

const facts = loadFacts(JSON.parse(readFileSync(args.facts, 'utf8')))
const storyboard = JSON.parse(readFileSync(args.storyboard, 'utf8'))
mkdirSync(args.out, { recursive: true })
mkdirSync(`${args.out}/png`, { recursive: true })

// ── gate 1：storyboard 前置检查 ──
const sbChecks = checkStoryboard(storyboard, facts)
if (sbChecks.errs.length) {
  console.error('check-storyboard ERROR（构建前拦截）：')
  sbChecks.errs.forEach(e => console.error('  🔴 ' + e))
  process.exit(1)
}

// ── 构建 ──
const templateReport = applyThemeOverrides(args.template)
const slug = storyboard.slug ?? 'deck'
const built = await buildDeck({ storyboard, facts, templateReport })
const pptxPath = `${args.out}/${slug}.pptx`
renameSync(built.file, pptxPath)
console.log(`✓ PPTX: ${pptxPath}（${storyboard.slides.length} 页，原生可编辑）`)

// ── gate 2：结构 QA（几何模型）──
const slideChecks = checkSlides(built.geometry, built.slidesResolved, facts, storyboard)

// ── gate 3：渲染 QA（PDF + PNG + 像素 + 文本断言）──
let renderResult = { errs: [], pngs: [] }, bleed = [], pdfText = { errs: [], pdfPages: 0 }
if (!args['no-pdf'] && !args['qa-only']) {
  const pdf = exportPdf(pptxPath, args.out)
  renderResult = renderPngs(pdf, `${args.out}/png`, storyboard.slides.length)
  pdfText = pdfTextCheck(pdf, built.slidesResolved.map(s => s.title))
  bleed = await edgeBleedCheck(`${args.out}/png`, renderResult.pngs)
  console.log(`✓ PDF: ${pdf}（${pdfText.pdfPages} 页）｜PNG: ${renderResult.pngs.length} 张 @150dpi`)
}

// ── QA 报告 ──
const { json, md } = writeQaReport({
  outDir: args.out, storyboard, factsMeta: facts.meta, templateReport,
  storyboardChecks: sbChecks, slideChecks, renderResult, bleed, pdfText,
  deckMeta: { ...storyboard.deck, slug },
})
writeFileSync(`${args.out}/qa-report.json`, JSON.stringify(json, null, 2))
writeFileSync(`${args.out}/qa-report.md`, md)

const errN = json.errCount
for (const s of json.sections) s.errs.forEach(e => console.error('  🔴 ' + e))
for (const s of json.sections) s.warns.forEach(w => console.warn('  🟡 ' + w))
console.log(`QA：${json.verdict}（ERROR ${errN} / WARN ${json.warnCount}）→ ${args.out}/qa-report.md`)
process.exit(errN === 0 ? 0 : 1)
