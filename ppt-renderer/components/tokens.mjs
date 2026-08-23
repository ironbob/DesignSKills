// 设计令牌：16:9 画布、统一栅格、字号纪律、色板（与 doc-renderer chartTheme 同源观感）
// 单位：英寸（pptxgenjs 原生单位）；字号 pt
export const CANVAS = { W: 10, H: 5.625 }

export const MARGIN = { top: 0.34, right: 0.5, bottom: 0.34, left: 0.5 }

// 栅格：顶部标签行 → 结论标题 → 内容区 → 底部来源行
export const GRID = {
  tagY: 0.32, tagH: 0.24,
  titleY: 0.58, titleH: 0.58,
  ruleY: 1.22, ruleW: 0.55, ruleH: 0.035,
  bodyY: 1.42, bodyH: 3.48,   // 内容区下缘 4.90
  srcY: 5.08, srcH: 0.28,
}

export const COLOR = {
  accent: '2563EB',      // 渠道蓝/主色（对齐 doc-renderer CHART_TOKENS.accent）
  accentSoft: 'DBEAFE',
  ink: '0F172A',
  label: '475569',
  muted: '64748B',
  grey: 'CBD5E1',
  greyDeep: '64748B',    // 堆叠图浅色段（白字可读）
  grid: 'E2E8F0',
  paper: 'FFFFFF',
  panel: 'F8FAFC',
  panelBorder: 'E2E8F0',
  good: '16A34A',
  goodSoft: 'DCFCE7',
  risk: 'DC2626',
  riskSoft: 'FEE2E2',
  warn: 'D97706',
  warnSoft: 'FEF3C7',
}

export const FONT = { sans: 'PingFang SC', latin: 'Helvetica Neue' }

// 字号纪律（10in 宽画布；正文 14pt ≈ 13.3in 画布的 18.7pt，投屏可读下限）
export const TYPE = {
  coverTitle: 32,
  coverSub: 15,
  slideTitle: 23,
  tag: 10.5,
  thesis: 14.5,
  kpi: 32,
  kpiDelta: 12.5,
  kpiLabel: 11,
  body: 13.5,
  bodySm: 12,
  step: 12,
  stepSub: 10,
  chartLabel: 10,
  chip: 10.5,
  source: 9,
  ask: 13.5,
}

// 文本行高倍数（显式设置，保证折行估算确定性）
export const LINE_H = 1.32

// 每版式正文区文字上限（中文字符，防文字墙；标题/来源行/notes 不计）
export const DENSITY_LIMIT = { perSlide: 320, perBlock: 130 }
