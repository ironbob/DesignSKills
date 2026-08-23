<script setup lang="ts">
// 预览框架（核心内容族）：五类产物一框架、tab ≤1 击切换、HTML 按目标端画布 1:1/46% 双档
// md 用 marked 渲染成排版文档；json 等文本走代码块；html 走同源 iframe
import { computed, ref, watch } from 'vue'
import { marked } from 'marked'
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
const isMd = computed(() => selected.value.endsWith('.md'))

const loading = ref(false)
const loadError = ref('')
const rawText = ref('')
const mdHtml = ref('')

watch(
  previewUrl,
  async (url) => {
    rawText.value = ''
    mdHtml.value = ''
    loadError.value = ''
    if (!url || isHtml.value) return
    loading.value = true
    try {
      const res = await fetch(url)
      if (!res.ok) throw new Error(`${res.status}`)
      rawText.value = await res.text()
      if (isMd.value) mdHtml.value = await marked.parse(rawText.value)
    } catch (e) {
      loadError.value = e instanceof Error ? e.message : String(e)
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

// json 缩进美化，其余文本原样
const prettyText = computed(() => {
  if (!rawText.value) return ''
  if (selected.value.endsWith('.json')) {
    try {
      return JSON.stringify(JSON.parse(rawText.value), null, 2)
    } catch {
      return rawText.value
    }
  }
  return rawText.value
})
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
        v-if="isHtml && previewUrl"
        :src="previewUrl"
        :sandbox="isHtml ? 'allow-same-origin' : undefined"
        class="pviframe"
      ></iframe>
      <div v-else-if="loading" class="pvempty">加载中…</div>
      <div v-else-if="loadError" class="pvempty">加载失败：{{ loadError }}</div>
      <div v-else-if="mdHtml" class="pvdoc">
        <div class="md-body" v-html="mdHtml"></div>
      </div>
      <pre v-else-if="prettyText" class="pvdoc"><code class="pvcode">{{ prettyText }}</code></pre>
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
.pvdoc {
  align-self: stretch;
  flex: 1;
  width: 100%;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  background: #fff;
  border: 1px solid #c7cbd3;
  border-radius: var(--r-card);
  margin: 0;
}
.pvcode {
  display: block;
  padding: var(--sp-3) var(--sp-4);
  font-family: var(--font-mono);
  font-size: var(--fs-caption);
  line-height: 1.7;
  color: var(--ink);
  white-space: pre-wrap;
  word-break: break-word;
}
/* markdown 排版（v-html 内容需 :deep） */
.md-body {
  max-width: 860px;
  margin: 0 auto;
  padding: var(--sp-5) var(--sp-5) var(--sp-6);
  font-size: var(--fs-body-l);
  line-height: 1.75;
  color: var(--ink);
  word-break: break-word;
}
.md-body :deep(h1) { font-size: var(--fs-display); font-weight: 800; line-height: 1.3; margin: 0 0 var(--sp-4); }
.md-body :deep(h2) {
  font-size: var(--fs-title);
  font-weight: 700;
  line-height: 1.4;
  margin: var(--sp-5) 0 var(--sp-2);
  padding-bottom: var(--sp-2);
  border-bottom: 1px solid var(--line);
}
.md-body :deep(h3) { font-size: var(--fs-body-l); font-weight: 700; margin: var(--sp-4) 0 var(--sp-2); }
.md-body :deep(h4) { font-size: var(--fs-body); font-weight: 700; margin: var(--sp-3) 0 var(--sp-2); }
.md-body :deep(p) { margin: 0 0 var(--sp-3); }
.md-body :deep(ul), .md-body :deep(ol) { margin: 0 0 var(--sp-3); padding-left: 1.5em; }
.md-body :deep(li) { margin: var(--sp-1) 0; }
.md-body :deep(li > ul), .md-body :deep(li > ol) { margin: var(--sp-1) 0; }
.md-body :deep(blockquote) {
  margin: 0 0 var(--sp-3);
  padding: 10px var(--sp-3);
  border-left: 3px solid var(--accent);
  background: var(--accent-surface);
  border-radius: 0 var(--r-small) var(--r-small) 0;
  color: var(--ink-weak);
}
.md-body :deep(blockquote p) { margin: 0; }
.md-body :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.88em;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 4px;
  padding: 1px 5px;
}
.md-body :deep(pre) {
  margin: 0 0 var(--sp-3);
  padding: var(--sp-3);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--r-card);
  overflow: auto;
}
.md-body :deep(pre code) { background: none; border: none; padding: 0; }
.md-body :deep(table) { border-collapse: collapse; width: 100%; margin: 0 0 var(--sp-3); font-size: var(--fs-body); }
.md-body :deep(th), .md-body :deep(td) { border: 1px solid var(--line); padding: 8px 12px; text-align: left; vertical-align: top; }
.md-body :deep(th) { background: var(--surface); font-weight: 700; }
.md-body :deep(hr) { border: none; border-top: 1px solid var(--line); margin: var(--sp-4) 0; }
.md-body :deep(a) { color: var(--accent); }
.md-body :deep(img) { max-width: 100%; border-radius: var(--r-card); }
.pvempty { color: var(--ink-weak); font-size: var(--fs-body); text-align: center; line-height: 2; }
.dim2 { font-size: var(--fs-caption); color: #9ca3af; }
</style>
