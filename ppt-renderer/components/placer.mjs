// Placer：pptxgenjs 调用的薄包装——每次放置同时记录几何与文本元数据，
// 供 check-slides 做重叠/越界/折行/字号/密度检查（几何模型与渲染同源，不二次手量）
import { CANVAS, LINE_H } from './tokens.mjs'

export class Placer {
  constructor(slide) {
    this.slide = slide
    this.elements = []   // {kind,x,y,w,h,layer,fontSize?,text?,name?}
  }

  /** layer: 'bg'（面板/色带，允许被前景压住）| 'fg'（前景，两两不得重叠） */
  text(text, opts, layer = 'fg', name = '') {
    this.slide.addText(text, opts)
    const runs = Array.isArray(text) ? text : null
    // run 混排：fontSize=设计字号（反 shrink 断言用）；wrapSize=加权折行字号（容量估算用）；bold 任一 run 加粗即计
    let wrapSize = opts.fontSize ?? 12
    if (runs?.length) {
      const total = runs.reduce((s, r) => s + (r.text ?? '').length, 0)
      if (total > 0) {
        wrapSize = runs.reduce((s, r) => s + (r.text ?? '').length * (r.options?.fontSize ?? opts.fontSize ?? 12), 0) / total
      }
    }
    this.elements.push({
      kind: 'text', name,
      x: opts.x, y: opts.y, w: opts.w, h: opts.h,
      layer, fontSize: opts.fontSize ?? 12, wrapSize,
      bold: (opts.bold ?? false) || Boolean(runs?.some(r => r.options?.bold)),
      text: typeof text === 'string' ? text : runs.map(r => r.text ?? '').join(''),
      align: opts.align, shrink: opts.fit === 'shrink',
    })
  }

  shape(slide, type, opts, layer = 'bg', name = '') {
    slide.addShape(type, opts)
    this.elements.push({
      kind: 'shape', name,
      x: opts.x, y: opts.y, w: opts.w, h: opts.h, layer, isLine: type === 'line',
    })
  }

  chart(pres, slide, type, data, opts, name = '') {
    slide.addChart(type, data, opts)
    this.elements.push({
      kind: 'chart', name,
      x: opts.x, y: opts.y, w: opts.w, h: opts.h, layer: 'fg',
      chartMeta: { type, data },
    })
  }

  /** CJK≈1em、ASCII≈0.55em 的每行容量估算（pt 域） */
  static estLines(text, fontSizePt, boxWIn) {
    if (!text) return 0
    const boxWPt = boxWIn * 72
    let lines = 0
    for (const para of String(text).split('\n')) {
      let wPt = 0
      let n = 1
      for (const ch of para) {
        const cw = /[⺀-鿿豈-﫿＀-￯]/.test(ch) ? fontSizePt : fontSizePt * 0.55
        if (wPt + cw > boxWPt) { n++; wPt = cw } else { wPt += cw }
      }
      lines += n
    }
    return lines
  }

  static estTextH(text, fontSizePt, boxWIn) {
    return (Placer.estLines(text, fontSizePt, boxWIn) * fontSizePt * LINE_H) / 72
  }

  /** 全文宽度估算（pt 域）——文字面积/填充率用 */
  static estTextW(text, fontSizePt) {
    let wPt = 0
    for (const ch of String(text ?? '')) {
      wPt += /[⺀-鿿豈-﫿＀-￯]/.test(ch) ? fontSizePt : fontSizePt * 0.55
    }
    return wPt
  }
}

export const inCanvas = el =>
  el.x >= -0.01 && el.y >= -0.01 &&
  el.x + el.w <= CANVAS.W + 0.01 && el.y + el.h <= CANVAS.H + 0.01
