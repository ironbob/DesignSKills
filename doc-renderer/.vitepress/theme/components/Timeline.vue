<script setup lang="ts">
export interface TimelineItem {
  title: string
  period?: string
  desc?: string
  accent?: boolean
}
defineProps<{ items: TimelineItem[] }>()
</script>

<template>
  <div class="timeline">
    <div v-for="(it, i) in items" :key="i" class="tl-item" :class="{ accent: it.accent }">
      <div class="tl-head">
        <span class="tl-title">{{ it.title }}</span>
        <span v-if="it.period" class="tl-period">{{ it.period }}</span>
      </div>
      <div v-if="it.desc" class="tl-desc">{{ it.desc }}</div>
    </div>
  </div>
</template>

<style scoped>
.timeline {
  margin: 1.2rem 0;
}
.tl-item {
  position: relative;
  padding: 0 0 22px 26px;
  border-left: 2px solid var(--doc-line);
}
.tl-item:last-child {
  padding-bottom: 4px;
  border-left-color: transparent;
}
.tl-item::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 3px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--doc-faint);
}
.tl-item.accent {
  border-left-color: var(--doc-accent-weak);
}
.tl-item.accent::before {
  background: var(--doc-accent);
  box-shadow: 0 0 0 4px var(--doc-accent-weak);
}
.tl-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.tl-title {
  font-weight: 700;
  font-size: 15.5px;
  color: var(--vp-c-text-1);
}
.tl-period {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--doc-muted);
  border: 1px solid var(--doc-line);
  border-radius: 99px;
  padding: 1px 10px;
  white-space: nowrap;
}
.tl-item.accent .tl-period {
  color: var(--doc-accent);
  border-color: var(--doc-accent-weak);
  background: var(--doc-accent-weak);
}
.tl-desc {
  margin-top: 4px;
  font-size: 14px;
  color: var(--doc-muted);
  line-height: 1.65;
}
</style>
