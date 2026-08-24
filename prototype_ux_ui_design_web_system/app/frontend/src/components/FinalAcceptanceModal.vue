<script setup lang="ts">
// rapid 最终验收弹窗：一次整体验收/导出确认（最终规格 + 关键默认决策 + U-x + 🟡 处置 + 契约文件）
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()

interface DefaultDecision {
  stage: number
  question_id: string | null
  question: string
  answer: string
  reason: string | null
  created_at: string
}
interface AcceptanceData {
  design_mode: string
  spec: string
  contract_files: { path: string; kind: string }[]
  default_decisions: DefaultDecision[]
  u_items: { id: string; text: string; proposal: string }[]
  yellow_dispositions: { id: string; dim: number | undefined; evidence: string; disposition: string }[]
}

const data = ref<AcceptanceData | null>(null)
const error = ref('')
const submitting = ref(false)
const confirmed = ref(false)

onMounted(async () => {
  if (!wb.project) return
  try {
    data.value = await api<AcceptanceData>(`/api/projects/${wb.project.id}/acceptance`)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})

async function submit() {
  if (!wb.project) return
  submitting.value = true
  error.value = ''
  try {
    await api(`/api/projects/${wb.project.id}/acceptance`, {
      method: 'POST',
      body: JSON.stringify({ reason: 'rapid 收口：核阅规格/默认决策/U-x/🟡 处置后确认' }),
    })
    wb.acceptanceOpen = false
    await wb.load(wb.project.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="overlay">
    <div class="dialog">
      <div class="dhead">
        <h3>最终验收 · 导出确认</h3>
        <span class="sub">rapid 模式收口：一次核阅，不回退 4/5 多轮选择</span>
      </div>

      <div v-if="error && !data" class="loading">{{ error }}</div>
      <div v-else-if="!data" class="loading">验收数据加载中…</div>

      <template v-else>
        <section>
          <h4>① 最终规格与契约文件（可导出/预览）</h4>
          <div class="files">
            <span v-for="f in data.contract_files" :key="f.path" class="file mono">{{ f.path }}</span>
          </div>
          <p class="hint">预览区可查看 {{ data.spec }}；契约=spec + tokens + 07-hifi 参照帧，可直接交给下游编码。</p>
        </section>

        <section>
          <h4>② 关键默认决策（rapid 自动采用，台账可推翻）</h4>
          <div v-if="!data.default_decisions.length" class="hint">本流程无 rapid_default 决策（全部为人工拍板）。</div>
          <div v-for="(d, i) in data.default_decisions" :key="i" class="drow">
            <span class="dstage">阶段{{ d.stage }} · {{ d.question_id }}</span>
            <span class="dq">{{ d.question }}</span>
            <span class="da">→ <b>{{ d.answer }}</b></span>
            <span v-if="d.reason" class="dr">{{ d.reason }}</span>
          </div>
        </section>

        <section>
          <h4>③ 未决 U-x（编码按倾向实现，留切换）</h4>
          <div v-if="!data.u_items.length" class="hint">无未决项。</div>
          <div v-for="u in data.u_items" :key="u.id" class="drow">
            <span class="dstage">{{ u.id }}</span>
            <span class="dq">{{ u.text }}</span>
            <span class="da">→ <b>{{ u.proposal }}</b></span>
          </div>
        </section>

        <section>
          <h4>④ 🟡 处置（🔴 已由 gate 强制清零）</h4>
          <div v-if="!data.yellow_dispositions.length" class="hint">无 🟡 findings。</div>
          <div v-for="y in data.yellow_dispositions" :key="y.id" class="drow">
            <span class="dstage">{{ y.id }}</span>
            <span class="dq">{{ y.evidence }}</span>
            <span class="da">→ <b>{{ y.disposition }}</b></span>
          </div>
        </section>

        <label class="exrow">
          <input v-model="confirmed" type="checkbox" />
          我已核阅以上内容，确认最终交付（记台账 source=final_acceptance · 落最终快照）
        </label>

        <p v-if="error" class="error">{{ error }}</p>

        <div class="dfoot">
          <button class="btn" @click="wb.acceptanceOpen = false">再看看</button>
          <span class="sp"></span>
          <button class="btn pri" :disabled="submitting || !confirmed" @click="submit">
            {{ submitting ? '提交中…' : '确认最终交付 · 项目完成' }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.28);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  z-index: 40;
}
.dialog {
  width: 840px;
  max-height: 100%;
  overflow: auto;
  background: #fff;
  border-radius: var(--r-panel);
  padding: 26px 30px;
  box-shadow: 0 12px 40px rgba(25, 27, 31, 0.18);
  box-sizing: border-box;
}
.dhead { display: flex; align-items: baseline; gap: 14px; }
h3 { margin: 0 0 3px; font-size: 18px; font-weight: 800; }
.sub { font-size: var(--fs-caption); color: var(--ink-weak); }
section { margin-top: 18px; }
h4 { margin: 0 0 8px; font-size: 13px; color: var(--ink-weak); font-weight: 700; letter-spacing: 0.03em; }
.files { display: flex; flex-wrap: wrap; gap: 8px; }
.file { border: 1px solid var(--line); border-radius: var(--r-small); padding: 4px 10px; font-size: var(--fs-caption); background: var(--surface); }
.mono { font-family: var(--font-mono); }
.hint { font-size: var(--fs-caption); color: var(--ink-weak); line-height: 1.7; margin: 4px 0; }
.drow { display: flex; gap: 10px; align-items: baseline; border-bottom: 1px solid #f0f1f3; padding: 8px 2px; font-size: var(--fs-caption); }
.dstage { flex: 0 0 92px; color: var(--ink-weak); font-weight: 700; }
.dq { flex: 1; color: #374151; }
.da { flex: 0 0 220px; color: #4b5563; }
.da b { color: var(--ink); }
.dr { flex: 0 0 200px; color: #9ca3af; }
.exrow { display: flex; gap: 8px; align-items: center; margin-top: 16px; font-size: var(--fs-caption); color: var(--accent); font-weight: 700; }
.error { color: var(--danger); font-size: var(--fs-caption); margin: 10px 0 0; }
.dfoot { display: flex; gap: 10px; margin-top: 16px; align-items: center; }
.sp { flex: 1; }
.btn { border: 1px solid #c7cbd3; border-radius: var(--r-small); padding: 10px 18px; font-size: var(--fs-ui); background: #fff; color: #374151; cursor: pointer; }
.btn.pri { background: var(--accent); color: #fff; font-weight: 700; border-color: var(--accent); min-width: 130px; }
.btn.pri:disabled { opacity: 0.45; cursor: not-allowed; }
.loading { color: var(--ink-weak); text-align: center; padding: 30px 0; }
</style>
