<script setup lang="ts">
// S5a 问题单（参照 07-hifi/s5a-questions.html 两帧）：卡片逐题 + 选项三件套 + 汇总拍板仪式
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
interface DecisionData {
  type: 'question_form' | 'confirm'
  stage: number
  stage_name: string
  data?: { blocking: Blocking[]; defaults: { id: string; text: string; value: string }[]; success_criteria: string[] }
}

const meta = ref<DecisionData | null>(null)
const error = ref('')
const idx = ref(0)
const answers = ref<Record<string, string>>({})
const submitting = ref(false)
const showSummary = ref(false)

onMounted(async () => {
  if (!wb.project) return
  try {
    meta.value = await api<DecisionData>(`/api/projects/${wb.project.id}/decision/${wb.project.current_stage}`)
    if (meta.value.type === 'confirm') {
      // 阶段 2+：确认型决策直接呈现汇总
      showSummary.value = true
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})

const blocking = computed(() => meta.value?.data?.blocking ?? [])
const current = computed(() => blocking.value[idx.value])
const answeredCount = computed(() => Object.keys(answers.value).length)
const allAnswered = computed(() => blocking.value.every((q) => answers.value[q.id]))

function pick(qid: string, label: string) {
  answers.value[qid] = label
}

async function submit() {
  if (!wb.project) return
  submitting.value = true
  error.value = ''
  try {
    const payload = {
      answers: Object.entries(answers.value).map(([id, answer]) => ({ id, answer })),
      accepted_defaults: (meta.value?.data?.defaults ?? []).map((d) => ({ id: d.id, text: d.text, value: d.value })),
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
          <p class="bnote">B 类默认假设 {{ meta.data.defaults.length }} 条随提交一并生效，可在台账里推翻</p>
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

      <!-- 确认型决策（阶段 2+） -->
      <template v-else-if="meta?.type === 'confirm'">
        <h3>阶段 {{ meta.stage }} · {{ meta.stage_name }} · 确认走向</h3>
        <p class="sub">确认=记台账+快照落盘+解锁阶段 {{ meta.stage + 1 }}；流程图可在预览区先看。</p>
        <p v-if="error" class="error">{{ error }}</p>
        <div class="dfoot">
          <button class="btn" @click="wb.questionOpen = false">再看一遍产物</button>
          <span class="sp"></span>
          <button class="btn pri" :disabled="submitting" @click="submit">
            {{ submitting ? '提交中…' : '确认 · 进下一阶段' }}
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
</style>
