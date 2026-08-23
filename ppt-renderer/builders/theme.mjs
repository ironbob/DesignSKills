// 主题层：无模板用默认 tokens；有用户模板时解包 theme1.xml，
// 提取 accent/ink/fonts 作为视觉约束（master/layout 结构由本渲染器的版式库承载）
import { execFileSync } from 'node:child_process'
import { COLOR, FONT } from '../components/tokens.mjs'

export function applyThemeOverrides(pptxPath) {
  if (!pptxPath) return { applied: false, note: '无模板：使用默认 layout library' }
  const xml = execFileSync('unzip', ['-p', pptxPath, 'ppt/theme/theme1.xml'], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 })
  const pick = tag => {
    const m = xml.match(new RegExp(`<a:${tag}>[\\s\\S]*?val="([0-9A-Fa-f]{6})"`))
    return m?.[1]?.toUpperCase()
  }
  const major = xml.match(/<a:majorFont>\s*<a:latin typeface="([^"]*)"/)?.[1]
  const majorEa = xml.match(/<a:majorFont>[\s\S]*?<a:ea typeface="([^"]*)"/)?.[1]
  const minor = xml.match(/<a:minorFont>\s*<a:latin typeface="([^"]*)"/)?.[1]
  const applied = {}
  const accent = pick('accent1')
  if (accent) { COLOR.accent = accent; applied.accent = accent }
  const dk1 = pick('dk2')
  if (dk1) { COLOR.ink = dk1; applied.ink = dk1 }
  const dk2lt = pick('lt2')
  if (dk2lt) { COLOR.greyDeep = dk2lt; applied.greyDeep = dk2lt }
  if (major || majorEa) { FONT.sans = majorEa || major; applied.fontSans = FONT.sans }
  if (minor) { FONT.latin = minor; applied.fontLatin = minor }
  return { applied: Object.keys(applied).length > 0, values: applied, note: `模板视觉约束已应用：${JSON.stringify(applied)}` }
}
