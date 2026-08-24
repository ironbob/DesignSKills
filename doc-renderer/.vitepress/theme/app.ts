import type { EnhanceAppContext } from 'vitepress'
import KpiRow from './components/KpiRow.vue'
import FigureChart from './components/FigureChart.vue'
import Callout from './components/Callout.vue'
import CompareMatrix from './components/CompareMatrix.vue'
import Timeline from './components/Timeline.vue'

export function enhanceApp({ app }: EnhanceAppContext) {
  app.component('KpiRow', KpiRow)
  app.component('FigureChart', FigureChart)
  app.component('Callout', Callout)
  app.component('CompareMatrix', CompareMatrix)
  app.component('Timeline', Timeline)
}
