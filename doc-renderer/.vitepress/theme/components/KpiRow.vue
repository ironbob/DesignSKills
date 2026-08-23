<script setup lang="ts">
export interface KpiItem {
  num: string
  unit?: string
  label: string
  delta?: string
  deltaType?: 'up' | 'down-good' | 'flat'
}

withDefaults(defineProps<{ items: KpiItem[]; cols?: number }>(), { cols: 0 })

function colCount(items: KpiItem[], cols: number) {
  return `repeat(${cols || items.length}, minmax(0, 1fr))`
}
</script>

<template>
  <div class="kpi-row" :style="{ gridTemplateColumns: colCount(items, cols) }">
    <div v-for="(k, i) in items" :key="i" class="kpi">
      <div class="kpi-num">{{ k.num }}<small v-if="k.unit">{{ k.unit }}</small></div>
      <div class="kpi-label">{{ k.label }}</div>
      <span v-if="k.delta" class="kpi-delta" :class="k.deltaType ?? 'flat'">{{ k.delta }}</span>
    </div>
  </div>
</template>

<style scoped>
.kpi-row {
  display: grid;
  gap: 14px;
  margin: 1.2rem 0 0.4rem;
}
.kpi {
  background: var(--doc-card);
  border: 1px solid var(--doc-line);
  border-radius: 14px;
  padding: 18px 16px;
}
.kpi-num {
  font-size: 48px;
  font-weight: 800;
  letter-spacing: -1.2px;
  line-height: 1.1;
  color: var(--vp-c-text-1);
  font-variant-numeric: tabular-nums;
}
.kpi-num small {
  font-size: 20px;
  font-weight: 700;
  margin-left: 1px;
}
.kpi-label {
  color: var(--doc-muted);
  font-size: 13.5px;
  margin-top: 6px;
}
.kpi-delta {
  display: inline-block;
  margin-top: 8px;
  font-size: 12.5px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 99px;
}
.kpi-delta.up { color: var(--doc-good); background: var(--doc-good-weak); }
.kpi-delta.down-good { color: var(--doc-accent); background: var(--doc-accent-weak); }
.kpi-delta.flat { color: var(--doc-muted); background: #f1f5f9; }
@media (max-width: 760px) {
  .kpi-num { font-size: 34px; }
}
</style>
