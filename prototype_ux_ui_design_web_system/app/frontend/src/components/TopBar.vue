<script setup lang="ts">
// 顶栏（全局常驻）：列表层=logo 锚点；项目层=面包屑（09-spec F-06 豁免记录的两级导航）
import HeartbeatPill from './HeartbeatPill.vue'

withDefaults(
  defineProps<{
    crumb?: string
    crumbDim?: string
    heartbeat?: 'idle' | 'queued' | 'running' | 'failed'
    heartbeatLabel?: string
    usage?: string
  }>(),
  { crumb: '', crumbDim: '', heartbeat: 'idle', heartbeatLabel: '空闲 · 无任务', usage: '' },
)

const emit = defineEmits<{ back: [] }>()
</script>

<template>
  <header class="topbar">
    <template v-if="crumb">
      <span class="crumb" @click="emit('back')">{{ crumb }}</span>
      <span v-if="crumbDim" class="dim">› {{ crumbDim }}</span>
    </template>
    <span v-else class="logo">AI 设计工作台</span>
    <HeartbeatPill :state="heartbeat" :label="heartbeatLabel" />
    <span class="sp"></span>
    <span v-if="usage" class="usage">{{ usage }}</span>
    <span class="linkbtn">设置</span>
  </header>
</template>

<style scoped>
.topbar {
  flex: 0 0 var(--topbar-h);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  border-bottom: 1px solid var(--line);
  background: #fff;
  font-size: var(--fs-ui);
}
.logo { font-weight: 800; font-size: 14px; }
.crumb { font-weight: 700; cursor: pointer; }
.crumb:hover { color: var(--accent); }
.dim { color: var(--ink-weak); font-weight: 400; }
.usage { font-size: var(--fs-caption); color: var(--ink-weak); }
.sp { flex: 1; }
.linkbtn {
  border: 1px solid var(--line);
  border-radius: var(--r-small);
  padding: 7px 14px;
  background: #fff;
  color: #374151;
  font-size: 12px;
  cursor: pointer;
}
</style>
