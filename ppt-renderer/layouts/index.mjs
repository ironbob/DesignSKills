// 版式注册表：storyboard.layout → 渲染器
// 约束：一页只承载一个主结论；标题即结论；不做 dashboard 式卡片堆砌
// 每个版式导出契约：FONT_SPEC（设计字号，反 shrink）/ HERO_NAMES（主视觉元素）/ KEY_ELEMENTS（缩略图关键元素）
import * as title from './title.mjs'
import * as execSummary from './exec-summary.mjs'
import * as conclusionChart from './conclusion-chart.mjs'
import * as mechanism from './mechanism.mjs'
import * as riskAction from './risk-action.mjs'
import * as decisionAsk from './decision-ask.mjs'
import * as roadmap from './roadmap.mjs'

export const LAYOUTS = {
  'title': title,
  'exec-summary': execSummary,
  'conclusion-chart': conclusionChart,
  'mechanism': mechanism,
  'risk-action': riskAction,
  'decision-ask': decisionAsk,
  'roadmap': roadmap,
}

/** 需要决策闭环字段检查的版式（计划/决策页） */
export const PLAN_LAYOUTS = new Set(['risk-action', 'decision-ask'])
