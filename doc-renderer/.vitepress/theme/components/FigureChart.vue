<script setup lang="ts">
import * as echarts from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { withTheme, type EChartsOption } from '../chartTheme'

const props = withDefaults(
  defineProps<{
    option: EChartsOption
    caption: string
    source?: string
    fallback: string
    height?: number
  }>(),
  { height: 300, source: '' },
)

const el = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let observer: ResizeObserver | null = null

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value, null, { renderer: 'svg' })
  chart.setOption(withTheme(props.option))
}

onMounted(() => {
  render()
  observer = new ResizeObserver(() => chart?.resize())
  if (el.value) observer.observe(el.value)
})

watch(() => props.option, render)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <figure class="doc-figure">
    <div ref="el" class="figure-chart" :style="{ height: height + 'px' }">{{ fallback }}</div>
    <figcaption>{{ caption }}</figcaption>
    <div v-if="source" class="figure-source">{{ source }}</div>
  </figure>
</template>

<style scoped>
.figure-chart {
  width: 100%;
  color: var(--doc-muted);
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
