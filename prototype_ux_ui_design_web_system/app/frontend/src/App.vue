<script setup lang="ts">
// 两级钻入无路由（09-spec §3）：产品列表 ↔ 项目工作台；S1 空态/向导浮层由 ui store 驱动
import { useUiStore } from '@/stores/ui'
import { connectSSE } from '@/lib/sse'
import ProductsView from '@/pages/ProductsView.vue'
import WorkbenchView from '@/pages/WorkbenchView.vue'

const ui = useUiStore()
connectSSE() // 全局事件流：任务心跳/产物增量由此分发到各 store
</script>

<template>
  <ProductsView v-if="ui.view === 'products'" />
  <WorkbenchView v-else />
</template>
