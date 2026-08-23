<script setup lang="ts">
withDefaults(defineProps<{ type?: 'conclusion' | 'risk' | 'data' }>(), { type: 'conclusion' })
</script>

<template>
  <div class="callout" :class="`callout--${type}`">
    <slot />
  </div>
</template>

<style scoped>
.callout {
  border-left: 4px solid var(--doc-accent);
  background: var(--doc-accent-weak);
  border-radius: 0 10px 10px 0;
  padding: 13px 16px;
  margin: 1.2rem 0;
  font-weight: 600;
  font-size: 15.5px;
  line-height: 1.7;
}
.callout--risk { border-left-color: var(--doc-risk); background: var(--doc-risk-weak); }
.callout--data {
  border-left-color: var(--doc-faint);
  background: #f1f5f9;
  font-weight: 400;
  font-size: 13.5px;
  color: var(--doc-muted);
}
</style>
