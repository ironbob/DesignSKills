<script setup lang="ts">
// 预览框架（核心内容族）：五类产物一框架、tab ≤1 击切换、HTML 按目标端画布 1:1/46% 双档
import { computed, ref, watch } from 'vue'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()
const selected = ref<string>('')
const scale = ref<'fit' | 'full'>('fit')

const tabs = computed(() => wb.project?.artifacts ?? [])

watch(
  tabs,
  (list) => {
    if (!list.length) {
      selected.value = ''
      return
    }
    if (!list.some((a) => a.path === selected.value)) {
      // 默认选中：当前阶段编号开头的产物，否则最新一个
      const prefix = String(wb.project?.current_stage ?? 1).padStart(2, '0')
      selected.value = list.find((a) => a.path.startsWith(prefix))?.path ?? list[list.length - 1].path
    }
  },
  { immediate: true },
)

const previewUrl = computed(() =>
  wb.project && selected.value ? `/api/preview/${wb.project.id}/${selected.value}` : '',
)
const isHtml = computed(() => selected.value.endsWith('.html'))
</script>

<template>
  <div class="pvframe">
    <div class="pvbar">
      <span
        v-for="a in tabs"
        :key="a.path"
        class="ptab"
        :class="{ on: a.path === selected, dim: false }"
        @click="selected = a.path"
      >{{ a.path }}</span>
      <span class="sp"></span>
      <span v-if="isHtml" class="mini" :class="{ on: scale === 'fit' }" @click="scale = 'fit'">1:1</span>
      <span v-if="isHtml" class="mini" :class="{ on: scale === 'full' }" @click="scale = 'full'">适应</span>
    </div>
    <div class="pvstage" :data-scale="isHtml ? scale : 'full'">
      <iframe
        v-if="previewUrl"
        :src="previewUrl"
        :sandbox="isHtml ? 'allow-same-origin' : undefined"
        class="pviframe"
      ></iframe>
      <div v-else class="pvempty">
        产物生成后会出现在这里<br />
        <span class="dim2">阶段任务 → gate → 预览</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pvframe {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--focus-surface);
  overflow: hidden;
  border-radius: 0 var(--r-panel) 0 0;
}
.pvbar {
  display: flex;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
  overflow-x: auto;
  align-items: center;
}
.ptab {
  border: 1px solid var(--line);
  border-radius: var(--r-small);
  padding: 5px 10px;
  color: #4b5563;
  background: #fff;
  font-size: var(--fs-caption);
  font-family: var(--font-mono);
  white-space: nowrap;
  cursor: pointer;
}
.ptab.on { background: var(--accent); color: #fff; border-color: var(--accent); font-weight: 700; }
.sp { flex: 1; }
.mini {
  font-size: 11px;
  color: #4b5563;
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 4px 10px;
  background: #fff;
  cursor: pointer;
}
.mini.on { border-color: var(--accent); color: var(--accent); font-weight: 700; }
.pvstage {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  padding: var(--sp-3);
  background: var(--focus-surface);
}
.pviframe { border: 1px solid #c7cbd3; border-radius: var(--r-card); background: #fff; }
.pvstage[data-scale='fit'] .pviframe { width: 100%; height: 100%; }
.pvempty { color: var(--ink-weak); font-size: var(--fs-body); text-align: center; line-height: 2; }
.dim2 { font-size: var(--fs-caption); color: #9ca3af; }
</style>
