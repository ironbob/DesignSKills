// QA 汇总：所有 gate 结果 → qa-report.json + qa-report.md（交付契约的一部分）
// 视觉复核为人工/AI 环节：写 <out>/qa-visual-review.md，重建时自动拼回报告尾部的「视觉复核记录」段
import { readFileSync, existsSync } from 'node:fs'

export function writeQaReport({ outDir, storyboard, factsMeta, templateReport, storyboardChecks, slideChecks, renderResult, bleed, pdfText, deckMeta }) {
  const sections = [
    { name: 'storyboard 完整性（check-storyboard）', errs: storyboardChecks.errs, warns: storyboardChecks.warns },
    { name: '结构 QA（check-slides：页数/标题/密度/字号/折行/重叠/越界/占位符/图表数字=facts）', errs: slideChecks.errs, warns: slideChecks.warns },
    { name: '渲染 QA（PPTX→PDF→PNG 页数/标题落页）', errs: renderResult.errs, warns: [] },
    { name: '像素 QA（PNG 边缘溢出检测）', errs: [], warns: bleed.filter(b => b.ratio > 0.005).map(b => `${b.file} 边缘非背景像素 ${b.ratio}（疑似贴边/裁切）`) },
    { name: 'PDF 内容断言（pdftotext 逐页标题）', errs: pdfText.errs, warns: [] },
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
