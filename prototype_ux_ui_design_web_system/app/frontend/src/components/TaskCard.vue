<script setup lang="ts">
// 任务卡（右栏第一张）：心跳+步骤+产物增量（等宽）+ 日志开关位（P2-2）
import { computed } from 'vue'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()

const STATE_TEXT: Record<string, string> = {
  queued: '排队中',
  running: '执行中',
  auto_redo: '自动重做中（gate 拦截后）',
  gate_running: 'gate 校验中',
  review_running: 'L2 评审中（独立判据）',
  awaiting_decision: '已完成 · 待你拍板',
  awaiting_acceptance: '九阶段完成 · 待最终验收',
  failed_needs_human: '失败 · 待人工处理',
  completed: '已完成',
}

const stateText = computed(() => {
  const t = wb.project?.current_task
  if (!t) return null
  return STATE_TEXT[t.state] ?? t.state
})

// 上一阶段的 completed 任务不占任务卡：新阶段 ready 时显示发起按钮
const activeTask = computed(() => {
  const t = wb.project?.current_task
  if (!t || t.state === 'completed') return null
  return t
})

const showIncrements = computed(() => wb.increments.slice(0, 6))

// L2 findings：SSE 实时优先；刷新页回退到任务行的 review_output
const findings = computed(() => {
  if (wb.reviewFindings.length) return wb.reviewFindings
  const raw = wb.project?.current_task?.review_output
  if (!raw) return []
  try {
    return JSON.parse(raw) as typeof wb.reviewFindings
  } catch {
    return []
  }
})
const reds = computed(() => findings.value.filter((f) => f.severity === 'red'))
const yellows = computed(() => findings.value.filter((f) => f.severity === 'yellow'))
</script>

<template>
  <div class="card" v-if="wb.project">
    <template v-if="activeTask">
      <h4><span class="dot" :data-s="activeTask.state"></span>任务 · {{ stateText }}</h4>
      <div v-if="wb.steps.length" class="steps">
        <div v-for="(s, i) in wb.steps.slice(-4)" :key="i" class="step" :class="{ last: i === Math.min(wb.steps.length, 4) - 1 }">
          {{ i === Math.min(wb.steps.length, 4) - 1 ? '▸' : '✓' }} {{ s }}
        </div>
      </div>
      <div v-if="showIncrements.length" class="files">
        <div v-for="p in showIncrements" :key="p" class="ok mono">{{ p }}</div>
      </div>
      <div v-if="findings.length" class="review">
        <div class="rv-head">
          L2 评审 ·
          <span class="rv-red">🔴 {{ reds.length }}</span>
          <span class="rv-yel">🟡 {{ yellows.length }}</span>
          <span v-if="!reds.length" class="rv-pass">（🔴=0 → 过）</span>
        </div>
        <div v-for="f in findings" :key="f.id" class="rv-item" :data-sev="f.severity">
          <b>{{ f.severity === 'red' ? '🔴' : '🟡' }} {{ f.criterion }}</b>
          <span v-if="f.evidence">{{ f.evidence }}</span>
          <span v-if="f.suggestion" class="rv-sug">建议：{{ f.suggestion }}</span>
        </div>
      </div>
      <span class="mini">日志 ▾（把关人）</span>
    </template>
    <template v-else>
      <h4><span class="dot" data-s="idle"></span>任务</h4>
      <p class="idle-hint">发起后约 1 分钟出产物 · 期间可离开</p>
      <button v-if="wb.stageState === 'ready'" class="primary" @click="wb.startStage(wb.project.current_stage)">
        发起阶段 {{ wb.project.current_stage }} 任务
      </button>
    </template>
  </div>
</template>

<style scoped>
.card {
  border: 1px solid var(--line);
  border-radius: var(--r-card);
  background: #fff;
  padding: 13px 15px;
}
h4 { margin: 0 0 9px; font-size: 11px; color: var(--ink-weak); font-weight: 700; display: flex; gap: 7px; align-items: center; letter-spacing: 0.03em; }
.dot { width: 9px; height: 9px; border-radius: 50%; background: #9ca3af; display: inline-block; }
.dot[data-s='running'], .dot[data-s='auto_redo'], .dot[data-s='gate_running'], .dot[data-s='review_running'], .dot[data-s='queued'] { background: var(--accent); }
.dot[data-s='awaiting_decision'], .dot[data-s='awaiting_acceptance'], .dot[data-s='completed'] { background: var(--sem-pass); }
.dot[data-s='failed_needs_human'] { background: var(--danger); }
.steps { font-size: var(--fs-ui); font-weight: 700; line-height: 1.9; margin-bottom: 6px; }
.steps .step { color: var(--ink-weak); font-weight: 400; font-size: var(--fs-caption); }
.steps .step.last { color: var(--ink); font-weight: 700; font-size: var(--fs-ui); }
.files { border-top: 1px dashed var(--line); margin-top: 6px; padding-top: 6px; }
.files .ok { color: var(--sem-pass); font-size: 11px; line-height: 1.9; }
.review { border-top: 1px dashed var(--line); margin-top: 6px; padding-top: 6px; font-size: var(--fs-caption); }
.rv-head { font-weight: 700; display: flex; gap: 8px; align-items: baseline; margin-bottom: 4px; }
.rv-red { color: var(--danger); }
.rv-yel { color: #b45309; }
.rv-pass { color: var(--sem-pass); font-weight: 400; }
.rv-item { border-left: 2px solid var(--line); padding: 3px 0 3px 8px; margin-bottom: 4px; line-height: 1.6; }
.rv-item[data-sev='red'] { border-left-color: var(--danger); }
.rv-item[data-sev='yellow'] { border-left-color: #d97706; }
.rv-item b { display: block; font-size: var(--fs-caption); }
.rv-item span { display: block; color: var(--ink-weak); }
.rv-sug { color: #4b5563 !important; }
.mini { font-size: 11px; color: #4b5563; border: 1px solid var(--line); border-radius: 5px; padding: 4px 9px; display: inline-block; margin-top: 9px; background: #fff; }
.idle-hint { font-size: var(--fs-caption); color: var(--ink-weak); margin: 4px 0 10px; }
.primary {
  width: 100%;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--r-small);
  padding: 10px 0;
  font-size: var(--fs-ui);
  font-weight: 700;
  cursor: pointer;
}
</style>
