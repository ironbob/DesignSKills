/**
 * Danci 数据层重构方案图表数据层 —— 数字与 docs/2026-08-23-danci-data-layer/02-事实台账.md 同源
 * option 只写数据+意图（类目/排序/强调哪些柱），观感统一由 chartTheme.withTheme 注入
 */
import { rankBars, type EChartsOption } from '../theme/chartTheme'

/**
 * 节 5 · 五项核心指标改善幅度（排序横向柱）
 * 强调意图：提速三项（查询/冷启动/写入）accent，资源两项（内存/体积）灰阶
 * 数据同源：F-12~F-16（变化基数=Core Data 现状）
 */
export const perfImprovement: EChartsOption = rankBars(
  [
    { label: '数据库文件体积', value: 17, text: '-17%' },
    { label: '内存峰值', value: 30, text: '-30%' },
    { label: '批量写入 1 万条', value: 61, text: '-61%', emphasize: true },
    { label: '冷启动首次加载', value: 62, text: '-62%', emphasize: true },
    { label: '复杂查询（SRS 调度）', value: 65, text: '-65%', emphasize: true },
  ],
  '改善幅度（%）',
  75,
)
