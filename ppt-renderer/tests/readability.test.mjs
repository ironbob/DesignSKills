// 演讲可读性 QA 测试（spec：docs/2026-08-24-ppt-readability-qa/spec.md §5）
// 10 个应失败（F01–F10）+ 5 个应通过（P01–P05）
import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { loadFacts } from '../builders/resolve.mjs'
import { checkStoryboard } from '../checks/check-storyboard.mjs'
import { checkSlides } from '../checks/check-slides.mjs'
import { applyVisualReview } from '../checks/qa.mjs'

const facts = loadFacts({
  facts: [
    { id: 'F-1', label: '订单详情 P99', value: 78, display: '78', unit: 'ms',
      baseline: { value: 210, display: '210' }, deltaDisplay: '−63%', source: '监控平台', confidence: 'measured' },
    { id: 'F-2', label: '大促峰值支付 QPS', value: 5200, display: '5,200', source: '压测报告', confidence: 'measured' },
    { id: 'F-3', label: '人工对账工单', value: 9, display: '9',
      baseline: { value: 120, display: '120' }, deltaDisplay: '−92.5%', source: '工单后台', confidence: 'measured' },
    { id: 'F-4', label: '新人上手周期', value: 3.5, display: '3.5', unit: '周',
      baseline: { value: 6, display: '6' }, deltaDisplay: '−42%', source: '转正评审', confidence: 'measured' },
  ],
})

const NOTES = {
  talk: '这一页的演讲稿写足六十字以上用来通过既有的 notes 完整性检查，口径与假设都放在这里而不是塞进页面正文，页面只保留结论与必要证据。',
  sources: ['口径：测试夹具（虚构数字）'],
}

const deck = () => ({ title: '测试汇报', audience: 'TL', purpose: '测试', minutes: 10, aspect: '16:9' })
const sbOf = slides => ({ slug: 't', deck: deck(), slides })

const ccSlide = over => ({
  no: 1, layout: 'conclusion-chart', tag: '专项',
  title: '订单拆分收益：P99 {{F-1.deltaDisplay}}，迁移零故障',
  chart: { type: 'metricsBar', catLabels: ['改造前', '改造后'],
    metrics: [{ label: '订单详情 P99（ms）', baselineFact: 'F-1.baseline', currentFact: 'F-1', format: '#,##0' }] },
  takeaways: ['背景：单体订单中心牵一发动全身', '动作：独立负责查询服务与事件总线'],
  source: '来源：测试', facts: ['F-1'], notes: NOTES, ...over,
})

// ── 应失败 F01–F10 ────────────────────────────────────────────

test('F01 conclusion-chart 三条辅助说明 → ERROR（版式语义）', () => {
  const sl = ccSlide({ takeaways: ['背景：单体牵一发动全身', '动作：独立负责两块设计', '结果：迁移期间线上零故障'] })
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.ok(errs.some(e => e.includes('辅助说明 3 条 > 2')), errs.join('\n'))
})

test('F02 标题讲 QPS（F-2）主图讲工单（F-3）→ 结论—证据错位 ERROR', () => {
  const sl = ccSlide({
    title: '大促零资损：峰值 {{F-2}} QPS 背后是三道防线',
    chart: { type: 'groupedBar', labels: ['对账工单（单/月）'], format: '#,##0',
      series: [{ name: '治理前', factValues: ['F-3.baseline'] }, { name: '治理后', factValues: ['F-3'] }] },
    facts: ['F-2', 'F-3'],
  })
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.ok(errs.some(e => e.includes('F-2 未由主视觉直接表达')), errs.join('\n'))
})

test('F03 decision-ask 三项请求 → ERROR（≤2，废紧凑三卡通道）', () => {
  const req = i => ({ what: `请求事项${i}`, target: '接口迁出并对齐水位', baseline: '订单域已验证',
    resources: '协作同学两名', owner: '本人', deadline: '2026-12-15 前启动' })
  const sl = { no: 1, layout: 'decision-ask', title: '请授权两条主线扩展', askLine: '请 TL 拍板排期授权与协作人力',
    requests: [req(1), req(2), req(3)], source: '来源：测试', notes: NOTES }
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.ok(errs.some(e => e.includes('请求 3 项 > 2')), errs.join('\n'))
})

test('F04 exec-summary 长 thesis + 风险+四KPI+ask 四模块同屏 → ERROR', () => {
  const sl = { no: 1, layout: 'exec-summary', title: '结论：两专项兑现能力可复制',
    thesis: '订单专项把核心接口耗时大幅压降发布耗时同步缩短大促峰值零降级零资损新人上手周期减半改善全部来自机制沉淀而不是期末冲刺这样够长了吗还不够继续加长到超过四十八字',
    risks: ['跨团队推动偏慢（见不足页）', '分享深度不均（见不足页）'],
    ask: '请授权推广到履约域与资金链路',
    kpis: [
      { label: '订单 P99', value: '{{F-1.value}}', unit: 'ms', deltaDisplay: '{{F-1.deltaDisplay}}' },
      { label: '对账工单', value: '{{F-3.value}}', unit: '单/月', deltaDisplay: '{{F-3.deltaDisplay}}' },
      { label: '峰值支付', value: '{{F-2.value}}', unit: 'QPS', deltaDisplay: '零资损' },
      { label: '上手周期', value: '{{F-4.value}}', unit: '周', deltaDisplay: '{{F-4.deltaDisplay}}' },
    ],
    source: '来源：测试', notes: NOTES }
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.ok(errs.some(e => e.includes('同屏')), errs.join('\n'))
})

test('F05 标题 55 字超两行容量 52 → ERROR（投屏三秒前提）', () => {
  const longTitle = '这是一个特别长的标题用于测试两行容量上限它必须超过五十二个中文字符才能触发标题字数超限的错误判断继续加长到足够'
  assert.ok(longTitle.length > 52)
  const { errs } = checkStoryboard(sbOf([ccSlide({ title: longTitle })]), facts)
  assert.ok(errs.some(e => e.includes('两行容量')), errs.join('\n'))
})

test('F06 takeaway 渲染字号 10.5 < 设计 12.5 → shrink-to-fit ERROR', () => {
  const page = { no: 1, layout: 'conclusion-chart', title: '订单接口耗时大幅下降', elements: [
    { kind: 'text', name: 'tag', x: 0.5, y: 0.32, w: 6, h: 0.24, layer: 'fg', fontSize: 10.5, bold: true, text: '专项' },
    { kind: 'text', name: 'title', x: 0.5, y: 0.58, w: 9, h: 0.58, layer: 'fg', fontSize: 23, bold: true, text: '订单接口耗时大幅下降' },
    { kind: 'text', name: 'source', x: 0.5, y: 5.08, w: 8.2, h: 0.28, layer: 'fg', fontSize: 9, text: '来源：测试' },
    { kind: 'text', name: 'pageno', x: 9.1, y: 5.08, w: 0.4, h: 0.28, layer: 'fg', fontSize: 9, text: '1 / 1' },
    { kind: 'chart', name: 'chart-grouped', x: 0.5, y: 1.5, w: 5.85, h: 3.3, layer: 'fg', chartMeta: { type: 'bar', data: [] } },
    { kind: 'text', name: 'cc-takeaway-0', x: 6.6, y: 1.58, w: 2.9, h: 0.92, layer: 'fg', fontSize: 10.5, wrapSize: 10.5, bold: false, text: '背景：单体牵一发动全身' },
  ] }
  const sb = sbOf([ccSlide()])
  const { errs } = checkSlides([page], [{ no: 1, layout: 'conclusion-chart' }], facts, sb)
  assert.ok(errs.some(e => e.includes('渲染字号 10.5 < 设计 12.5')), errs.join('\n'))
})

test('F07 单条 takeaway 92 字 → 单块超上限 60 ERROR（禁右栏长段落）', () => {
  const long = '这是一条特别长的辅助说明用于验证单文本块字数上限它必须超过六十个中文字符才能触发右栏禁长段落的错误判断所以还需要继续写很多字直到明显超过上限为止继续加长'.slice(0, 92)
  const { errs } = checkStoryboard(sbOf([ccSlide({ takeaways: [long, '动作：独立负责两块设计'] })]), facts)
  assert.ok(errs.some(e => e.includes('超上限 60')), errs.join('\n'))
})

test('F08 图表缩至 3.2×2.4in（占比 22%）→ 主视觉占比 ERROR', () => {
  const page = { no: 1, layout: 'conclusion-chart', title: '订单接口耗时大幅下降', elements: [
    { kind: 'text', name: 'tag', x: 0.5, y: 0.32, w: 6, h: 0.24, layer: 'fg', fontSize: 10.5, bold: true, text: '专项' },
    { kind: 'text', name: 'title', x: 0.5, y: 0.58, w: 9, h: 0.58, layer: 'fg', fontSize: 23, bold: true, text: '订单接口耗时大幅下降' },
    { kind: 'text', name: 'source', x: 0.5, y: 5.08, w: 8.2, h: 0.28, layer: 'fg', fontSize: 9, text: '来源：测试' },
    { kind: 'text', name: 'pageno', x: 9.1, y: 5.08, w: 0.4, h: 0.28, layer: 'fg', fontSize: 9, text: '1 / 1' },
    { kind: 'chart', name: 'chart-grouped', x: 0.5, y: 1.5, w: 3.2, h: 2.4, layer: 'fg', chartMeta: { type: 'bar', data: [] } },
    { kind: 'text', name: 'cc-takeaway-0', x: 6.6, y: 1.58, w: 2.9, h: 0.92, layer: 'fg', fontSize: 12.5, wrapSize: 12.5, bold: false, text: '背景：单体牵一发动全身' },
  ] }
  const sb = sbOf([ccSlide()])
  const { errs } = checkSlides([page], [{ no: 1, layout: 'conclusion-chart' }], facts, sb)
  assert.ok(errs.some(e => e.includes('主视觉占比')), errs.join('\n'))
})

test('F09 roadmap 承载 target/baseline/resources → 资源申请字段 ERROR', () => {
  const sl = { no: 1, layout: 'roadmap', title: 'H2 三条线：方法论复制与资产常态化',
    workstreams: [
      { what: '履约域微服务化推广', milestone: '2026-12-15 前首阶段拆分', owner: '本人',
        target: '接口迁出并对齐水位', baseline: '订单域已验证', resources: '协作同学两名' },
      { what: '稳定性资产常态化', milestone: '2026-11-30 SOP 成文', owner: '本人' },
      { what: '上手计划模板化', milestone: '2026-09-30 模板入库', owner: '本人' },
    ],
    source: '来源：测试', notes: NOTES }
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.ok(errs.some(e => e.includes('不得承载资源申请字段')), errs.join('\n'))
})

test('F10 视觉复核 threeSecond=2 → 整 deck FAIL（评分卡 gate）', () => {
  const dir = mkdtempSync(join(tmpdir(), 'vr-'))
  try {
    writeFileSync(join(dir, 'qa-visual-review.json'), JSON.stringify({
      reviewer: 'ai',
      slides: [{ no: 5, threeSecond: 2, heroProves: 5, noWall: 5, projectionReady: 5, nextAction: 5 }],
    }))
    const bad = applyVisualReview(dir)
    assert.ok(bad.errs.some(e => e.includes('三秒读出结论 得 2 分 < 4')), bad.errs.join('\n'))
    rmSync(join(dir, 'qa-visual-review.json'))
    const missing = applyVisualReview(dir)
    assert.ok(missing.errs.length === 0 && missing.warns.some(w => w.includes('视觉复核未完成')))
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

// ── 应通过 P01–P05 ────────────────────────────────────────────

test('P01 conclusion-chart：标题引用=图表 refs，takeaways 2×短 → gate1 无 ERROR', () => {
  const { errs } = checkStoryboard(sbOf([ccSlide()]), facts)
  assert.deepEqual(errs, [])
})

test('P02 decision-ask：两项请求全闭环字段 → gate1 无 ERROR', () => {
  const sl = { no: 1, layout: 'decision-ask', title: '请授权两条主线扩展',
    askLine: '请 TL 拍板排期授权；请总监协调资金链路联建',
    requests: [
      { what: '履约域拆分排期授权', target: '接口迁出并对齐水位', baseline: '订单域已验证',
        resources: '协作同学两名', owner: '本人', deadline: '2026-12-15 前启动' },
      { what: '资金链路对账联建', target: '资金对账自动化覆盖', baseline: '人工对账月均居高',
        resources: '风控财务各一名', owner: '本人加值班团队', deadline: '2026-11-30 前演练' },
    ],
    source: '来源：测试', notes: NOTES }
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.deepEqual(errs, [])
})

test('P03 exec-summary：短 thesis + 四模块并存 → gate1 无 ERROR', () => {
  const sl = { no: 1, layout: 'exec-summary', title: '结论：两专项兑现能力可复制',
    thesis: 'P99 与发布耗时大幅压降，大促零资损，改善来自机制沉淀可复制',
    risks: ['跨团队推动偏慢（见不足页）', '分享深度不均（见不足页）'],
    ask: '请授权推广到履约域与资金链路',
    kpis: [
      { label: '订单 P99', value: '{{F-1.value}}', unit: 'ms', deltaDisplay: '{{F-1.deltaDisplay}}' },
      { label: '对账工单', value: '{{F-3.value}}', unit: '单/月', deltaDisplay: '{{F-3.deltaDisplay}}' },
      { label: '峰值支付', value: '{{F-2.value}}', unit: 'QPS', deltaDisplay: '零资损' },
      { label: '上手周期', value: '{{F-4.value}}', unit: '周', deltaDisplay: '{{F-4.deltaDisplay}}' },
    ],
    source: '来源：测试', notes: NOTES }
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.deepEqual(errs, [])
})

test('P04 mechanism：2 行×3 步 + 运行结果条 → gate1 无 ERROR', () => {
  const sl = { no: 1, layout: 'mechanism', title: '读写分离扛读流量，事件总线解耦履约',
    flow: { rows: [
      { label: '查询服务', steps: [{ label: '读写分离', sub: '读流量切从库' }, { label: '本地缓存', sub: '热点前置' }, { label: 'P99 降至 {{F-1}}', tone: 'good' }] },
      { label: '事件总线', steps: [{ label: '事件发布', sub: '状态变更即发' }, { label: '订阅分发', sub: '下游按需消费' }, { label: '履约解耦', tone: 'good' }] },
    ], linkNote: '两线并行：发布互不等待' },
    evidence: '迁移核心接口零故障，日均调用稳定',
    source: '来源：测试', notes: NOTES }
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.deepEqual(errs, [])
})

test('P05 roadmap：三条工作流轻字段（无资源字段）→ gate1 无 ERROR', () => {
  const sl = { no: 1, layout: 'roadmap', title: 'H2 三条线：方法论复制与资产常态化',
    workstreams: [
      { what: '履约域微服务化推广', milestone: '2026-12-15 前首阶段拆分', owner: '本人' },
      { what: '稳定性资产常态化', milestone: '2026-11-30 SOP 成文', owner: '本人加值班团队' },
      { what: '上手计划模板化', milestone: '2026-09-30 模板入库', owner: '本人' },
    ],
    linkNote: '三条线均从沉淀长出',
    source: '来源：测试', notes: NOTES }
  const { errs } = checkStoryboard(sbOf([sl]), facts)
  assert.deepEqual(errs, [])
})
