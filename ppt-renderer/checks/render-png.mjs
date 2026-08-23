// 渲染与像素 QA：soffice 无头转 PDF → pdftoppm 逐页 PNG → 边缘溢出像素检测 + pdftotext 内容断言
import { execFileSync } from 'node:child_process'
import { readdirSync, existsSync } from 'node:fs'
import { PNG } from 'pngjs'

const SOFFICE = process.env.SOFFICE_BIN ?? '/Applications/LibreOffice.app/Contents/MacOS/soffice'

export function exportPdf(pptxPath, outDir) {
  execFileSync(SOFFICE, ['--headless', '--convert-to', 'pdf', '--outdir', outDir, pptxPath], {
    timeout: 120_000, stdio: 'pipe',
  })
  const pdf = `${outDir}/${pptxPath.split('/').pop().replace(/\.pptx$/, '')}.pdf`
  if (!existsSync(pdf)) throw new Error(`PDF 导出失败：${pdf} 不存在`)
  return pdf
}

export function renderPngs(pdfPath, pngDir, expectPages) {
  execFileSync('pdftoppm', ['-png', '-r', '150', pdfPath, `${pngDir}/slide`], { timeout: 120_000 })
  const pngs = readdirSync(pngDir).filter(f => f.endsWith('.png')).sort()
  const errs = []
  if (pngs.length !== expectPages) errs.push(`PNG 页数 ${pngs.length} ≠ deck 页数 ${expectPages}`)
  return { pngs, errs }
}

/** pdftotext 内容断言：每页标题必须出现在 PDF 对应页（验证 PPTX 与导出 PDF 一致） */
export function pdfTextCheck(pdfPath, titles) {
  const errs = []
  const pages = execFileSync('pdftotext', [pdfPath, '-'], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 })
    .split('\f')
  titles.forEach((t, i) => {
    const norm = s => s.replace(/\s+/g, '')
    if (!norm(pages[i] ?? '').includes(norm(t).slice(0, 12))) {
      errs.push(`PDF 第 ${i + 1} 页未见标题「${t}」（PPTX 与 PDF 可能不一致）`)
    }
  })
  return { errs, pdfPages: pages.length - (pages[pages.length - 1] === '' ? 1 : 0) }
}

/** 边缘溢出检测：页面四边 4px 带内非背景像素占比（内容贴边 = 越界/裁切信号） */
export async function edgeBleedCheck(pngDir, pngs) {
  const { readFile } = await import('node:fs/promises')
  const results = []
  for (const f of pngs) {
    const buf = await readFile(`${pngDir}/${f}`)
    const png = PNG.sync.read(buf)
    const { width, height } = png
    const band = 4
    let dark = 0, total = 0
    const lum = idx => 0.299 * png.data[idx] + 0.587 * png.data[idx + 1] + 0.114 * png.data[idx + 2]
    for (let x = 0; x < width; x++) {
      for (const y of [0, 1, 2, 3, height - 4, height - 3, height - 2, height - 1]) {
        total++
        if (lum((y * width + x) * 4) < 235) dark++
      }
    }
    for (let y = band; y < height - band; y++) {
      for (const x of [0, 1, 2, 3, width - 4, width - 3, width - 2, width - 1]) {
        total++
        if (lum((y * width + x) * 4) < 235) dark++
      }
    }
    results.push({ file: f, ratio: +(dark / total).toFixed(5) })
  }
  return results
}
