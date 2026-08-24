<script setup lang="ts">
// 任务心跳灯（全局常驻）：●执行中 / ○排队 / ✕失败 / 灰=空闲——符号+文字强制（规则 4/10）
defineProps<{
  state: 'idle' | 'queued' | 'running' | 'failed'
  label: string
}>()
</script>

<template>
  <span class="pill" :data-state="state">
    <span class="dot"></span>
    <span>{{ label }}</span>
  </span>
</template>

<style scoped>
.pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 12px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: var(--surface);
  color: #374151;
  font-size: 12px;
}
.dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #9ca3af;
}
.pill[data-state='running'] .dot { background: var(--accent); }
.pill[data-state='running'] { color: #374151; border-color: var(--line); }
.pill[data-state='failed'] .dot { background: var(--danger); }
.pill[data-state='failed'] {
  color: #7a2620;
  background: var(--danger-surface);
  border-color: var(--danger-line);
}
</style>
