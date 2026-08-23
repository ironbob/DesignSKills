<script setup lang="ts">
// S5a 决策弹窗：question_form 逐题拍板 / confirm 确认走向 / gallery 变体·方向挑选（可混搭）/ crit 处置审批
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()

interface Option {
  label: string
  recommend: boolean
  claim: string
  consequence: string
}
interface Blocking {
  id: string
  text: string
  situation: string
  scope?: string
  options: Option[]
}
interface GalleryOption {
  label: string
  preview: string
}
interface GalleryItem {
  id: string
  text: string
  options: GalleryOption[]
  mixable: boolean
}
interface CritFinding {
  id: string
  dim: number
  severity: string
  location: string
  evidence: string
  proposed: string
}
interface CritU {
  id: string
  text: string
  proposal: string
}
interface DecisionData {
  type: 'question_form' | 'confirm' | 'gallery' | 'crit'
  stage: number
  stage_name: string
  data?:
    | { blocking: Blocking[]; defaults: { id: string; text: string; value: string }[]; success_criteria: string[] }
    | { items: GalleryItem[] }
    | { yellows: CritFinding[]; u_items: CritU[] }
}

const meta = ref<DecisionData | null>(null)
const error = ref('')
const idx = ref(0)
const answers = ref<Record<string, string>>({})
const submitting = ref(false)
const showSummary = ref(false)

// gallery：逐项选择 + 可选混搭备注（记台账可审计）
const galPicks = ref<Record<string, string>>({})
const mixNotes = ref<Record<string, string>>({})
// crit：🟡 三选一处置 + U-x 倾向确认；豁免须显式勾选确认
const critChoices = ref<Record<string, string>>({})
const uAnswers = ref<Record<string, string>>({})
const exemptConfirmed = ref(false)

onMounted(async () => {
  if (!wb.project) return
  try {
    meta.value = await api<DecisionData>(`/api/projects/${wb.project.id}/decision/${wb.project.current_stage}`)
    if (meta.value.type === 'confirm') {
      showSummary.value = true
    }
    if (meta.value.type === 'crit' && meta.value.data && 'yellows' in meta.value.data) {
      meta.value.data.yellows.forEach((f) => (critChoices.value[f.id] = f.proposed || 'fix'))
      meta.value.data.u_items.forEach((u) => (uAnswers.value[u.id] = u.proposal))
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})

const blocking = computed(() => (meta.value?.data && 'blocking' in meta.value.data ? meta.value.data.blocking : []))
const qDefaults = computed(() => (meta.value?.data && 'defaults' in meta.value.data ? meta.value.data.defaults : []))
const current = computed(() => blocking.value[idx.value])
const answeredCount = computed(() => Object.keys(answers.value).length)
const allAnswered = computed(() => blocking.value.every((q) => answers.value[q.id]))

const galleryItems = computed(() => (meta.value?.data && 'items' in meta.value.data ? meta.value.data.items : []))
const galleryDone = computed(() => galleryItems.value.every((it) => galPicks.value[it.id]))

const critYellows = computed(() => (meta.value?.data && 'yellows' in meta.value.data ? meta.value.data.yellows : []))
const critU = computed(() => (meta.value?.data && 'u_items' in meta.value.data ? meta.value.data.u_items : []))
const hasExempt = computed(() => Object.values(critChoices.value).some((v) => v === 'exempt'))
const critDone = computed(
  () =>
    critYellows.value.every((f) => critChoices.value[f.id]) &&
    critU.value.every((u) => uAnswers.value[u.id]?.trim()) &&
    (!hasExempt.value || exemptConfirmed.value),
)

function pick(qid: string, label: string) {
  answers.value[qid] = label
}

function galAnswer(it: GalleryItem): string {
  const label = galPicks.value[it.id]
  const note = mixNotes.value[it.id]?.trim()
  return note ? `混搭：${label} 基底 · ${note}` : label
}

async function submit() {
  if (!wb.project) return
  submitting.value = true
  error.value = ''
  try {
    let payload: Record<string, unknown>
    if (meta.value?.type === 'gallery') {
      payload = { answers: galleryItems.value.map((it) => ({ id: it.id, answer: galAnswer(it) })) }
    } else if (meta.value?.type === 'crit') {
      payload = {
        answers: [
          ...critYellows.value.map((f) => ({ id: f.id, answer: critChoices.value[f.id] })),
          ...critU.value.map((u) => ({ id: u.id, answer: uAnswers.value[u.id] })),
        ],
        confirm_exemptions: hasExempt.value && exemptConfirmed.value,
      }
    } else {
      payload = {
        answers: Object.entries(answers.value).map(([id, answer]) => ({ id, answer })),
        accepted_defaults:
          meta.value?.data && 'defaults' in (meta.value.data as Record<string, unknown>)
            ? ((meta.value.data as { defaults: { id: string; text: string; value: string }[] }).defaults ?? []).map(
                (d) => ({ id: d.id, text: d.text, value: d.value }),
              )
            : [],
      }
    }
    await api(`/api/projects/${wb.project.id}/stages/${wb.project.current_stage}/decision`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    wb.questionOpen = false
    await wb.load(wb.project.id) // 重新拉取：阶段轨推进 + 快照生效
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
      <template v-if="meta?.type === 'question_form' && meta.data">
        <!-- 汇总拍板仪式 -->
        <div v-if="showSummary" class="dhead">
          <h3>{{ blocking.length }} 题已答完</h3>
          <span class="sub">提交即拍板进台账 · 快照落盘 · 逐条可改</span>
        </div>
        <div v-else class="dhead">
          <h3>阶段 {{ meta.stage }} · {{ meta.stage_name }}</h3>
          <span class="sub">每题都有推荐与后果 · 可暂存（切走不丢）</span>
        </div>

        <!-- 逐题卡 -->
        <div v-if="!showSummary" class="prog">
          第 {{ idx + 1 }} / {{ blocking.length }} 题
          <span class="pips">
            <span v-for="(q, i) in blocking" :key="q.id" class="pip" :class="{ on: i <= idx, answered: !!answers[q.id] }"></span>
          </span>
        </div>

        <div v-if="!showSummary && current" class="qcard">
          <div class="qid">{{ current.id }} · 影响范围：{{ current.scope ?? '全局' }}</div>
          <div class="qtext">{{ current.text }}</div>
          <p class="qsitu">{{ current.situation }}</p>
          <div class="optrow">
            <div
              v-for="o in current.options"
              :key="o.label"
              class="opt"
              :class="{ recom: o.recommend, picked: answers[current.id] === o.label }"
              @click="pick(current.id, o.label)"
            >
              <span v-if="o.recommend" class="tag">推荐</span><span v-else class="tag ghost-tag">　</span>
              <div class="name">{{ o.label }}</div>
              <div class="why">{{ o.claim }}</div>
              <div class="warn">{{ o.consequence }}</div>
            </div>
          </div>
        </div>

        <!-- 汇总 -->
        <div v-if="showSummary" class="summary">
          <div v-for="q in blocking" :key="q.id" class="srow">
            <span class="sid">{{ q.id }}</span>
            <span class="sq">{{ q.text }}</span>
            <span class="sa"><b>{{ answers[q.id] || '未答' }}</b></span>
            <span class="edit" @click="showSummary = false; idx = blocking.findIndex(x => x.id === q.id)">改</span>
          </div>
          <p class="bnote">{{ wb.project?.design_mode === 'rapid'
            ? `快速模式：B 类默认假设 ${qDefaults.length} 条将自动采用（台账 source=rapid_default，可推翻）`
            : `B 类默认假设 ${qDefaults.length} 条随提交一并生效，可在台账里推翻` }}</p>
        </div>

        <p v-if="error" class="error">{{ error }}</p>

        <div class="dfoot">
          <template v-if="!showSummary">
            <button class="btn" :disabled="idx === 0" @click="idx--">← 上一题</button>
            <button v-if="idx < blocking.length - 1" class="btn pri" :disabled="!answers[current?.id]" @click="idx++">下一题 →</button>
            <button v-else class="btn pri" :disabled="!allAnswered" @click="showSummary = true">答完 · 看汇总</button>
            <span class="sp"></span>
            <span class="aside">已答 {{ answeredCount }}/{{ blocking.length }}</span>
          </template>
          <template v-else>
            <button class="btn" @click="showSummary = false">← 回题面</button>
            <span class="sp"></span>
            <button class="btn pri" :disabled="submitting || !allAnswered" @click="submit">
              {{ submitting ? '提交中…' : '提交拍板 · 快照 · 进下一阶段' }}
            </button>
          </template>
        </div>
      </template>

      <!-- 确认型决策（阶段 3/6/7/9 等） -->
      <template v-else-if="meta?.type === 'confirm'">
        <h3>阶段 {{ meta.stage }} · {{ meta.stage_name }} · 确认走向</h3>
        <p class="sub">确认=记台账+快照落盘+解锁阶段 {{ meta.stage + 1 }}；产物可在预览区先看。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="dfoot">
          <button class="btn" @click="wb.questionOpen = false">再看一遍产物</button>
          <span class="sp"></span>
          <button class="btn pri" :disabled="submitting" @click="submit">
            {{ submitting ? '提交中…' : '确认 · 进下一阶段' }}
          </button>
        </div>
      </template>

      <!-- 变体/方向挑选（阶段 4 关键屏灰框 · 阶段 5 视觉方向） -->
      <template v-else-if="meta?.type === 'gallery' && meta.data && 'items' in meta.data">
        <div class="dhead">
          <h3>阶段 {{ meta.stage }} · {{ meta.stage_name }} · 挑选</h3>
          <span class="sub">并排对比 · 点选 · 可混搭（记台账，随时可改）</span>
        </div>
        <div class="gitems">
          <div v-for="it in meta.data.items" :key="it.id" class="gitem">
            <div class="gt">{{ it.text }}</div>
            <div class="gopts">
              <div
                v-for="o in it.options"
                :key="o.label"
                class="gopt"
                :class="{ picked: galPicks[it.id] === o.label }"
                @click="galPicks[it.id] = o.label"
              >
                <div class="glab">{{ o.label }}<span v-if="galPicks[it.id] === o.label" class="gon">✓ 已选</span></div>
                <iframe
                  v-if="wb.project"
                  :src="`/api/preview/${wb.project.id}/${o.preview}`"
                  sandbox="allow-same-origin"
                  class="gframe"
                ></iframe>
              </div>
            </div>
            <div v-if="it.mixable" class="gmix">
              <label>混搭备注（可选）：如「V1 的反馈位置 + V2 的面板形态」</label>
              <input v-model="mixNotes[it.id]" class="gin" placeholder="选基础变体后填混搭要点" />
            </div>
          </div>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="dfoot">
          <button class="btn" @click="wb.questionOpen = false">再想想</button>
          <span class="sp"></span>
          <button class="btn pri" :disabled="submitting || !galleryDone" @click="submit">
            {{ submitting ? '提交中…'
              : galleryItems.every((it) => it.options.length === 1)
                ? '采用该方案 · 继续快速执行'
                : `拍板${meta.stage === 4 ? '变体' : '方向'} · 快照 · 进下一阶段` }}
          </button>
        </div>
      </template>

      <!-- crit 处置审批（阶段 8） -->
      <template v-else-if="meta?.type === 'crit' && meta.data && 'yellows' in meta.data">
        <div class="dhead">
          <h3>阶段 {{ meta.stage }} · {{ meta.stage_name }} · crit 处置审批</h3>
          <span class="sub">🔴 已由 gate 强制清零 · 此处审 🟡 处置与 U-x 倾向</span>
        </div>
        <div class="clist">
          <div v-for="f in meta.data.yellows" :key="f.id" class="crow">
            <div class="ctop">
              <b>🟡 {{ f.id }}</b><span class="cdim">维度 {{ f.dim }} · {{ f.location }}</span>
            </div>
            <p class="cev">{{ f.evidence }}</p>
            <div class="cseg">
              <button :class="{ on: critChoices[f.id] === 'fix' }" @click="critChoices[f.id] = 'fix'">修复</button>
              <button :class="{ on: critChoices[f.id] === 'spec' }" @click="critChoices[f.id] = 'spec'">进规格</button>
              <button
                :class="{ on: critChoices[f.id] === 'exempt', warn: critChoices[f.id] === 'exempt' }"
                @click="critChoices[f.id] = 'exempt'"
              >
                豁免
              </button>
            </div>
          </div>
          <div v-for="u in meta.data.u_items" :key="u.id" class="crow">
            <div class="ctop"><b>{{ u.id }} 未决</b><span class="cdim">{{ u.text }}</span></div>
            <label class="ulab">倾向方案（编码按倾向实现，留切换）</label>
            <input v-model="uAnswers[u.id]" class="gin" />
          </div>
        </div>
        <label v-if="hasExempt" class="exrow">
          <input v-model="exemptConfirmed" type="checkbox" />
          我确认以上豁免成立（豁免记台账，交付规格如实呈现）
        </label>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="dfoot">
          <button class="btn" @click="wb.questionOpen = false">再看看</button>
          <span class="sp"></span>
          <button class="btn pri" :disabled="submitting || !critDone" @click="submit">
            {{ submitting ? '提交中…' : '批准处置 · 快照 · 进下一阶段' }}
          </button>
        </div>
      </template>

      <div v-else class="loading">{{ error || '决策数据加载中…' }}</div>
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
.prog { display: flex; align-items: center; gap: 8px; margin: 14px 0; font-size: var(--fs-caption); color: var(--ink-weak); }
.pips { display: flex; gap: 6px; flex: 1; }
.pip { width: 52px; height: 6px; border-radius: 3px; background: #e7e9ee; }
.pip.on { background: var(--accent); }
.pip.answered { background: var(--ink); }
.qcard { border: 1px solid var(--line); border-radius: 10px; background: #fff; padding: 18px 20px; }
.qid { font-size: 11px; color: var(--ink-weak); font-weight: 700; }
.qtext { font-size: 17px; font-weight: 800; margin: 7px 0 5px; line-height: 1.5; }
.qsitu { font-size: var(--fs-caption); color: var(--ink-weak); margin: 0 0 14px; line-height: 1.7; }
.optrow { display: flex; gap: 12px; }
.opt {
  flex: 1;
  border: 1.5px solid #c7cbd3;
  border-radius: var(--r-card);
  padding: 13px 15px;
  background: #fff;
  cursor: pointer;
}
.opt.recom { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-surface); }
.opt.picked { border-color: var(--ink); box-shadow: none; background: var(--surface); }
.tag { display: inline-block; font-size: 10px; border: 1px solid var(--accent); border-radius: 3px; padding: 0 6px; color: var(--accent); font-weight: 700; margin-bottom: 7px; }
.ghost-tag { border-color: #e3e5ea; color: #e3e5ea; }
.opt .name { font-size: var(--fs-body); font-weight: 800; margin-bottom: 5px; }
.opt .why { font-size: var(--fs-caption); color: #4b5563; line-height: 1.65; }
.opt .warn { font-size: 11px; color: var(--ink-weak); margin-top: 8px; line-height: 1.6; border-top: 1px dashed var(--line); padding-top: 8px; }
.summary { margin-top: 14px; }
.srow { display: flex; gap: 14px; align-items: center; border-bottom: 1px solid #f0f1f3; padding: 11px 2px; font-size: var(--fs-ui); }
.sid { font-size: 11px; color: var(--ink-weak); font-weight: 700; flex: 0 0 36px; }
.sq { flex: 1; font-weight: 700; }
.sa { flex: 0 0 300px; font-size: var(--fs-caption); color: #4b5563; }
.edit { flex: 0 0 auto; font-size: 11px; color: var(--accent); font-weight: 700; cursor: pointer; }
.bnote { font-size: 11px; color: #9ca3af; margin: 10px 0 0; }
.error { color: var(--danger); font-size: var(--fs-caption); margin: 10px 0 0; }
.dfoot { display: flex; gap: 10px; margin-top: 16px; align-items: center; }
.sp { flex: 1; }
.aside { font-size: 11px; color: #9ca3af; }
.btn {
  border: 1px solid #c7cbd3;
  border-radius: var(--r-small);
  padding: 10px 18px;
  font-size: var(--fs-ui);
  background: #fff;
  color: #374151;
  cursor: pointer;
}
.btn:disabled { color: #c3c7ce; border-color: #e3e5ea; background: #fafbfc; cursor: not-allowed; }
.btn.pri { background: var(--accent); color: #fff; font-weight: 700; border-color: var(--accent); min-width: 130px; }
.btn.pri:disabled { opacity: 0.45; }
.loading { color: var(--ink-weak); text-align: center; padding: 30px 0; }
/* ---- gallery ---- */
.gitems { display: flex; flex-direction: column; gap: 18px; margin-top: 14px; }
.gitem { border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.gt { font-size: var(--fs-ui); font-weight: 800; margin-bottom: 10px; }
.gopts { display: flex; gap: 12px; }
.gopt { flex: 1; border: 1.5px solid #c7cbd3; border-radius: var(--r-card); padding: 10px; cursor: pointer; background: #fff; }
.gopt.picked { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-surface); }
.glab { font-size: var(--fs-ui); font-weight: 800; margin-bottom: 8px; display: flex; justify-content: space-between; }
.gon { color: var(--accent); font-size: 11px; }
.gframe { width: 100%; height: 340px; border: 1px solid var(--line); border-radius: 6px; background: #fff; }
.gmix { margin-top: 10px; }
.gmix label { display: block; font-size: 11px; color: var(--ink-weak); margin-bottom: 4px; }
.gin { width: 100%; box-sizing: border-box; border: 1px solid #c7cbd3; border-radius: 6px; padding: 9px 10px; font-size: var(--fs-ui); }
/* ---- crit ---- */
.clist { margin-top: 14px; display: flex; flex-direction: column; gap: 10px; }
.crow { border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px; }
.ctop { display: flex; align-items: baseline; gap: 10px; }
.ctop b { font-size: var(--fs-ui); }
.cdim { font-size: 11px; color: var(--ink-weak); }
.cev { font-size: var(--fs-caption); color: #4b5563; margin: 6px 0 10px; line-height: 1.7; }
.cseg { display: flex; gap: 8px; }
.cseg button { flex: 1; min-height: 40px; border: 1px solid #c7cbd3; background: #fff; border-radius: 6px; font-size: var(--fs-caption); cursor: pointer; color: #374151; }
.cseg button.on { background: var(--ink); color: #fff; border-color: var(--ink); font-weight: 700; }
.cseg button.on.warn { background: var(--danger); border-color: var(--danger); }
.ulab { display: block; font-size: 11px; color: var(--ink-weak); margin: 8px 0 4px; }
.exrow { display: flex; gap: 8px; align-items: center; margin-top: 12px; font-size: var(--fs-caption); color: var(--danger); font-weight: 700; }
</style>
