<script setup lang="ts">
// revision 阶段决策面板：confirm / gallery / crit（与主流程四类决策同一套校验语义，作用域=revision）
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useRevisionsStore } from '@/stores/revisions'

const rev = useRevisionsStore()
const meta = ref<null | { type: string; stage: number; stage_name: string; data?: any }>(null)
const error = ref('')
const galPicks = ref<Record<string, string>>({})
const critChoices = ref<Record<string, string>>({})
const uAnswers = ref<Record<string, string>>({})
const exemptConfirmed = ref(false)
const reason = ref('')

const stage = computed(() => rev.revision?.current_stage ?? 0)

async function load() {
  if (!rev.projectId || !rev.revision) return
  error.value = ''
  try {
    meta.value = await api(`/api/projects/${rev.projectId}/revisions/${rev.revision.id}/decision/${stage.value}`)
    if (meta.value?.type === 'crit' && meta.value.data) {
      meta.value.data.yellows?.forEach((f: any) => (critChoices.value[f.id] = f.proposed || 'fix'))
      meta.value.data.u_items?.forEach((u: any) => (uAnswers.value[u.id] = u.proposal))
    }
  } catch (e) {
    meta.value = null
    error.value = e instanceof Error ? e.message : String(e)
  }
}

async function submit() {
  if (!meta.value) return
  let payload: Record<string, unknown>
  if (meta.value.type === 'confirm') {
    payload = { answers: [{ id: `stage-${stage.value}-confirm`, answer: '确认增量产物' }], reason: reason.value }
  } else if (meta.value.type === 'gallery') {
    payload = { answers: Object.entries(galPicks.value).map(([id, answer]) => ({ id, answer })), reason: reason.value }
  } else {
    payload = {
      answers: [
        ...Object.entries(critChoices.value).map(([id, answer]) => ({ id, answer })),
        ...Object.entries(uAnswers.value).map(([id, answer]) => ({ id, answer })),
      ],
      reason: reason.value,
      confirm_exemptions: exemptConfirmed.value,
    }
  }
  const ok = await rev.decide(stage.value, payload)
  if (ok) {
    meta.value = null
    galPicks.value = {}
    critChoices.value = {}
    uAnswers.value = {}
    exemptConfirmed.value = false
  }
}

const galleryDone = computed(() =>
  meta.value?.type === 'gallery' && (meta.value.data?.items ?? []).every((it: any) => galPicks.value[it.id]))
const critDone = computed(() =>
  meta.value?.type === 'crit' &&
  (meta.value.data?.yellows ?? []).every((f: any) => critChoices.value[f.id]) &&
  (meta.value.data?.u_items ?? []).every((u: any) => uAnswers.value[u.id]))
const hasExempt = computed(() => Object.values(critChoices.value).some((v) => v === 'exempt'))
const canSubmit = computed(() =>
  meta.value?.type === 'confirm' || galleryDone.value || critDone.value)

onMounted(load)
defineExpose({ reload: load })
</script>

<template>
  <div class="card">
    <h4>阶段 {{ stage }} 拍板</h4>
    <p v-if="error" class="err">{{ error }}</p>
    <template v-if="meta?.type === 'confirm'">
      <p class="hint">确认「{{ meta.stage_name }}」增量产物（gate 已通过）→ 进下一受影响阶段。</p>
      <input v-model="reason" placeholder="拍板理由（可选，入台账）" />
    </template>
    <template v-else-if="meta?.type === 'gallery'">
      <div v-for="it in meta.data?.items ?? []" :key="it.id" class="q">
        <p class="qt">{{ it.text }}</p>
        <div class="opts">
          <label v-for="o in it.options" :key="o.label" class="opt" :class="{ on: galPicks[it.id] === o.label }">
            <input type="radio" :name="it.id" :value="o.label" v-model="galPicks[it.id]" />
            <span>{{ o.label }}</span>
          </label>
        </div>
        <a v-if="galPicks[it.id] && it.options.find((o: any) => o.label === galPicks[it.id])?.preview"
           class="pv" :href="`/api/preview/${rev.projectId}/revisions/${rev.revision?.id}/${it.options.find((o: any) => o.label === galPicks[it.id]).preview}`"
           target="_blank">预览选中方案 →</a>
      </div>
    </template>
    <template v-else-if="meta?.type === 'crit'">
      <div v-for="f in meta.data?.yellows ?? []" :key="f.id" class="q">
        <p class="qt">{{ f.id }} · {{ f.evidence }}</p>
        <div class="opts">
          <label v-for="v in ['fix', 'spec', 'exempt']" :key="v" class="opt" :class="{ on: critChoices[f.id] === v }">
            <input type="radio" :name="f.id" :value="v" v-model="critChoices[f.id]" />
            <span>{{ v === 'fix' ? '修复' : v === 'spec' ? '进规格' : '豁免' }}</span>
          </label>
        </div>
      </div>
      <div v-for="u in meta.data?.u_items ?? []" :key="u.id" class="q">
        <p class="qt">{{ u.id }} · {{ u.text }}</p>
        <input v-model="uAnswers[u.id]" placeholder="倾向方案" />
      </div>
      <label v-if="hasExempt" class="exempt">
        <input type="checkbox" v-model="exemptConfirmed" />
        豁免处置须显式确认（记台账，可追溯）
      </label>
    </template>
    <button v-if="meta" class="primary" :disabled="!canSubmit || rev.busy || (hasExempt && !exemptConfirmed)" @click="submit">
      拍板{{ meta.type === 'confirm' ? '并继续' : '' }}
    </button>
  </div>
</template>

<style scoped>
.card { border: 1px solid var(--line); border-radius: var(--r-card); background: #fff; padding: 13px 15px; display: flex; flex-direction: column; gap: 10px; }
h4 { margin: 0; font-size: 11px; color: var(--ink-weak); font-weight: 700; letter-spacing: 0.03em; }
.hint { margin: 0; font-size: var(--fs-caption); color: var(--ink-weak); line-height: 1.7; }
.err { margin: 0; font-size: 12px; color: var(--danger); }
input[type='text'], input:not([type]) { border: 1px solid var(--line); border-radius: var(--r-small); padding: 7px 9px; font-size: var(--fs-ui); }
.q { display: flex; flex-direction: column; gap: 6px; }
.qt { margin: 0; font-size: var(--fs-caption); color: #374151; line-height: 1.6; }
.opts { display: flex; gap: 8px; flex-wrap: wrap; }
.opt { display: flex; align-items: center; gap: 6px; border: 1px solid var(--line); border-radius: var(--r-small); padding: 6px 10px; font-size: 12px; cursor: pointer; background: #fff; }
.opt.on { border-color: var(--accent); color: var(--accent); font-weight: 700; }
.pv { font-size: 11px; color: var(--accent); }
.exempt { display: flex; gap: 7px; align-items: center; font-size: 12px; color: var(--sem-warn); font-weight: 600; }
.primary { background: var(--accent); color: #fff; border: none; border-radius: var(--r-small); padding: 9px 16px; font-weight: 700; cursor: pointer; }
.primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
