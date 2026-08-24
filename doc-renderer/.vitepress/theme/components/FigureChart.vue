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
  if (!chart) {
    // 降级文本只属于「无 JS/SSG」场景；客户端 init 前必须移除，
    // 否则它作为 flex 子项把图表行撑宽、图表整体右移溢出卡片
    el.value.querySelector('.figure-fallback')?.remove()
    chart = echarts.init(el.value, null, { renderer: 'svg' })
  }
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
    <div ref="el" class="figure-chart" :style="{ height: height + 'px' }">
      <span class="figure-fallback">{{ fallback }}</span>
    </div>
    <figcaption>{{ caption }}</figcaption>
    <div v-if="source" class="figure-source">{{ source }}</div>
  </figure>
</template>

<style scoped>
.figure-chart {
  position: relative;
  width: 100%;
}
/* 降级文本绝对定位铺满：即使残留也不参与 flex 布局、不挤压图表 */
.figure-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24px;
  color: var(--doc-muted);
  font-size: 14px;
  text-align: center;
}
</style>
