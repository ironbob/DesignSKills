// QA 汇总：所有 gate 结果 → qa-report.json + qa-report.md（交付契约的一部分）
// 视觉复核评分卡（spec §2.4）：读 <out>/qa-visual-review.json——任一维 <4 或非法 → ERROR（整 deck FAIL）；
// 未复核 → WARN 提示（交付前完成）；人工备注仍走 qa-visual-review.md，重建时拼回报告尾部
import { readFileSync, existsSync } from 'node:fs'

const REVIEW_DIMS = ['threeSecond', 'heroProves', 'noWall', 'projectionReady', 'nextAction']
const DIM_NAMES = { threeSecond: '三秒读出结论', heroProves: '主视觉证明结论', noWall: '无文字墙', projectionReady: '适合投屏', nextAction: '下一步明确' }

/** 视觉复核评分卡 gate：1–5 分制，任一维 <4 → ERROR（spec §2.4） */
export function applyVisualReview(outDir) {
  const path = `${outDir}/qa-visual-review.json`
  if (!existsSync(path)) {
    return { errs: [], warns: ['视觉复核未完成——交付前逐页查看 png/ 并写 qa-visual-review.json（任一维 <4 整 deck FAIL）'], scores: null }
  }
  let vr = null
  try { vr = JSON.parse(readFileSync(path, 'utf8')) } catch (e) {
    return { errs: [`qa-visual-review.json 解析失败：${e.message}`], warns: [], scores: null }
  }
  const errs = [], warns = []
  for (const s of vr.slides ?? []) {
    for (const dim of REVIEW_DIMS) {
      const v = s[dim]
      if (!Number.isInteger(v) || v < 1 || v > 5) errs.push(`slide ${s.no}: ${dim} 评分非法 ${JSON.stringify(v)}（须 1–5 整数）`)
      else if (v < 4) errs.push(`slide ${s.no}: ${DIM_NAMES[dim]} 得 ${v} 分 < 4——该页不达投屏标准`)
    }
  }
  return { errs, warns, scores: vr }
}

export function writeQaReport({ outDir, storyboard, factsMeta, templateReport, storyboardChecks, slideChecks, renderResult, bleed, pdfText, deckMeta }) {
  const visual = applyVisualReview(outDir)
  const sections = [
    { name: 'storyboard 完整性（check-storyboard：schema/结论式标题/决策闭环/裸数字禁令/内容预算/结论—证据一致/版式语义）', errs: storyboardChecks.errs, warns: storyboardChecks.warns },
    { name: '结构 QA（check-slides：页数/标题/折行/重叠/越界/占位符/图表数字=facts/投屏可读性）', errs: slideChecks.errs, warns: slideChecks.warns },
    { name: '渲染 QA（PPTX→PDF→PNG 页数/标题落页）', errs: renderResult.errs, warns: [] },
    { name: '像素 QA（PNG 边缘溢出检测）', errs: [], warns: bleed.filter(b => b.ratio > 0.005).map(b => `${b.file} 边缘非背景像素 ${b.ratio}（疑似贴边/裁切）`) },
    { name: 'PDF 内容断言（pdftotext 逐页标题）', errs: pdfText.errs, warns: [] },
    { name: '视觉复核评分卡（qa-visual-review.json：三秒结论/主视觉证明/无文字墙/适合投屏/下一步，任一维 <4 = FAIL）', errs: visual.errs, warns: visual.warns },
  ]
  const errCount = sections.reduce((s, x) => s + x.errs.length, 0)
  const warnCount = sections.reduce((s, x) => s + x.warns.length, 0)

  const json = {
    deck: deckMeta, verdict: errCount === 0 ? 'PASS' : 'FAIL',
    errCount, warnCount, template: templateReport,
    slides: storyboard.slides.length, factsUsed: factsMeta.facts.length,
    sections: sections.map(s => ({ name: s.name, errs: s.errs, warns: s.warns })),
    bleed,
  }

  const md = [
    `# PPT QA 记录`,
    ``,
    `- deck：${deckMeta.title}｜${storyboard.slides.length} 页｜16:9`,
    `- 判定：**${json.verdict}**（ERROR ${errCount} / WARN ${warnCount}）`,
    `- 模板：${templateReport.note}`,
    `- 生成：storyboard + facts 共享数据层 → pptxgenjs 原生可编辑 PPTX → LibreOffice PDF → pdftoppm PNG`,
    ``,
  ]
  for (const s of sections) {
    md.push(`## ${s.name}`)
    md.push(s.errs.length ? s.errs.map(e => `- 🔴 ${e}`).join('\n') : '- ✅ 无 ERROR')
    if (s.warns.length) md.push(s.warns.map(w => `- 🟡 ${w}`).join('\n'))
    md.push('')
  }
  if (visual.scores?.slides?.length) {
    md.push('## 视觉复核评分（qa-visual-review.json）')
    md.push('')
    md.push('| 页 | 三秒结论 | 主视觉证明 | 无文字墙 | 适合投屏 | 下一步 |')
    md.push('|---|---|---|---|---|---|')
    for (const s of visual.scores.slides) {
      md.push(`| ${s.no} | ${s.threeSecond ?? '—'} | ${s.heroProves ?? '—'} | ${s.noWall ?? '—'} | ${s.projectionReady ?? '—'} | ${s.nextAction ?? '—'} |`)
    }
    md.push('')
  }
  md.push('## 视觉复核记录（人工/AI 逐页）')
  const vr = `${outDir}/qa-visual-review.md`
  if (existsSync(vr)) {
    md.push(readFileSync(vr, 'utf8').trim())
  } else {
    md.push('> 交付前由执行方逐页查看 png/ 并将结论写入 <out>/qa-visual-review.md（重建报告时自动拼回此处）。')
  }
  md.push('')
  return { json, md: md.join('\n') }
}
