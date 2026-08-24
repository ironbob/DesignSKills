// 页面公共件：节标签、结论标题、accent 短线、来源行、页码
// 所有版式共用同一栅格，保证 deck 观感一致（编辑器中可整体替换主题色/字体）
import { GRID, COLOR, FONT, TYPE, MARGIN } from './tokens.mjs'

/** 标题区：节标签 + 结论式标题 + accent 短线 */
export function titleBlock(pl, { tag, title }) {
  if (tag) {
    pl.text(tag, {
      x: MARGIN.left, y: GRID.tagY, w: 6, h: GRID.tagH,
      fontSize: TYPE.tag, fontFace: FONT.sans, color: COLOR.accent, bold: true,
      characterSpacing: 1, align: 'left', valign: 'middle',
    }, 'fg', 'tag')
  }
  pl.text(title, {
    x: MARGIN.left, y: GRID.titleY, w: 9.0, h: GRID.titleH,
    fontSize: TYPE.slideTitle, fontFace: FONT.sans, color: COLOR.ink, bold: true,
    align: 'left', valign: 'middle',
  }, 'fg', 'title')
  pl.shape(pl.slide, 'rect', {
    x: MARGIN.left, y: GRID.ruleY, w: GRID.ruleW, h: GRID.ruleH,
    fill: { color: COLOR.accent }, line: { type: 'none' },
  }, 'bg', 'rule')
}

/** 底部来源行（口径+推算标记）+ 右侧页码 */
export function sourceFooter(pl, { source, pageNo, total }) {
  if (source) {
    pl.text(source, {
      x: MARGIN.left, y: GRID.srcY, w: 8.2, h: GRID.srcH,
      fontSize: TYPE.source, fontFace: FONT.sans, color: COLOR.muted,
      align: 'left', valign: 'middle',
    }, 'fg', 'source')
  }
  pl.text(`${pageNo} / ${total}`, {
    x: 9.1, y: GRID.srcY, w: 0.4, h: GRID.srcH,
    fontSize: TYPE.source, fontFace: FONT.latin, color: COLOR.muted,
    align: 'right', valign: 'middle',
  }, 'fg', 'pageno')
}

/** 公共元素设计字号（各版式 FONT_SPEC 的公共前缀；反 shrink-to-fit 断言依据） */
export const COMMON_FONT_SPEC = {
  tag: TYPE.tag, title: TYPE.slideTitle, source: TYPE.source, pageno: TYPE.source,
}

/** 面板底色（bg 层：前景文字可压在其上）。name：卡片计数区分用（flow-node 不计卡） */
export function panel(pl, { x, y, w, h, fill = COLOR.panel, lineColor = COLOR.panelBorder, radius = 0.06, name = 'panel' }) {
  pl.shape(pl.slide, 'roundRect', {
    x, y, w, h, rectRadius: radius,
    fill: { color: fill },
    line: lineColor ? { color: lineColor, width: 0.75 } : { type: 'none' },
  }, 'bg', name)
}

/** 左色条强调面板（风险/请求卡） */
export function accentPanel(pl, { x, y, w, h, barColor, fill = COLOR.panel }) {
  panel(pl, { x, y, w, h, fill, lineColor: COLOR.panelBorder })
  pl.shape(pl.slide, 'rect', {
    x, y: y + 0.06, w: 0.045, h: h - 0.12,
    fill: { color: barColor }, line: { type: 'none' },
  }, 'bg', 'accentbar')
}
