<script setup lang="ts">
// S3 阶段工作台（三区：阶段轨 208 / 预览台 / 右栏操作 336 —— 09-spec §5 S3）
import { computed, onMounted } from 'vue'
import TopBar from '@/components/TopBar.vue'
import StageRail from '@/components/StageRail.vue'
import ArtifactPreview from '@/components/ArtifactPreview.vue'
import TaskCard from '@/components/TaskCard.vue'
import DecisionCard from '@/components/DecisionCard.vue'
import QuestionFormModal from '@/components/QuestionFormModal.vue'
import { useUiStore } from '@/stores/ui'
import { useWorkbenchStore } from '@/stores/workbench'

const ui = useUiStore()
const wb = useWorkbenchStore()

onMounted(() => {
  if (ui.workbenchProjectId != null) void wb.load(ui.workbenchProjectId)
})

const crumb = computed(() => wb.project?.product_name ?? '…')
const crumbDim = computed(() =>
  wb.project ? `${wb.project.name}（${wb.project.canvas.width}×${wb.project.canvas.height}）` : '',
)

const HEART: Record<string, { s: 'idle' | 'queued' | 'running' | 'failed'; t: string }> = {
  idle: { s: 'idle', t: '空闲 · 无任务' },
  ready: { s: 'idle', t: '空闲 · 可发起' },
  queued: { s: 'queued', t: '排队中' },
  running: { s: 'running', t: `执行中 · 阶段 ${wb.project?.current_stage ?? ''}` },
  auto_redo: { s: 'running', t: '自动重做中' },
  gate_running: { s: 'running', t: 'gate 校验中' },
  review_running: { s: 'running', t: 'L2 评审中' },
  awaiting_decision: { s: 'idle', t: '空闲 · 待决策' },
  failed_needs_human: { s: 'failed', t: '失败 · 待人工' },
  completed: { s: 'idle', t: '空闲' },
}
const heart = computed(() => HEART[wb.stageState] ?? HEART.idle)

// 副标题按模式/决策类别说明本阶段停走规则
const curMeta = computed(() => wb.project?.decision_meta[String(wb.project?.current_stage)])
const modeHint = computed(() => {
  if (!wb.project) return ''
  const meta = curMeta.value
  const cat = meta ? `${meta.label}（${meta.human_decision ? '必停人工' : '可自动放行'}）` : ''
  if (wb.stageState === 'awaiting_decision') return 'gate 已通过 · 等你拍板后进下一阶段'
  return wb.project.run_mode === 'auto'
    ? `auto 模式 · 阶段 ${wb.project.current_stage} ${cat} · 事实类过双层 gate（L1 脚本 + L2 评审）自动推进`
    : '任务 → gate → 决策点 → 快照 · 一步一确认'
})
</script>

<template>
  <div class="page" v-if="wb.project">
    <TopBar :crumb="crumb" :crumb-dim="crumbDim" :heartbeat="heart.s" :heartbeat-label="heart.t" @back="ui.backToProducts()" />
    <div class="body">
      <StageRail />
      <div class="main">
        <div class="stagehead">
          <h2>阶段 {{ wb.project.current_stage }} · {{ wb.project.stage_names[wb.project.current_stage - 1] }}</h2>
          <p>{{ modeHint }}</p>
        </div>
        <ArtifactPreview />
      </div>
      <div class="ops">
        <TaskCard />
        <DecisionCard />
        <div class="card">
          <h4>本阶段完成标志</h4>
          <div class="done-list">
            <div>· 产物生成且 L1 gate 通过</div>
            <div>· L2 评审 🔴=0（判据卡 findings）</div>
            <div v-if="wb.project.run_mode === 'auto' && !curMeta?.human_decision">· auto 代批（答案类/品味类仍停人工）</div>
            <div v-else>· 决策点拍板（问题单/确认）</div>
            <div>· 快照落盘 · 台账留痕</div>
          </div>
        </div>
      </div>
    </div>
    <QuestionFormModal v-if="wb.questionOpen" />
  </div>
  <div v-else class="page"><div class="loading">{{ wb.error ? `加载失败：${wb.error}` : '加载中…' }}</div></div>
</template>

<style scoped>
.page { height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.loading { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--ink-weak); }
.body { flex: 1; display: flex; min-height: 0; }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; background: #fff; }
.stagehead { padding: 16px 24px 12px; border-bottom: 1px solid var(--line); background: #fff; }
.stagehead h2 { margin: 0; font-size: var(--fs-title); font-weight: 800; }
.stagehead p { margin: 4px 0 0; font-size: var(--fs-caption); color: var(--ink-weak); }
.ops {
  flex: 0 0 var(--ops-w);
  border-left: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: var(--sp-3);
  box-sizing: border-box;
  overflow-y: auto;
  background: #fff;
}
.card { border: 1px solid var(--line); border-radius: var(--r-card); background: #fff; padding: 13px 15px; }
.card h4 { margin: 0 0 8px; font-size: 11px; color: var(--ink-weak); font-weight: 700; letter-spacing: 0.03em; }
.done-list { font-size: var(--fs-caption); color: var(--ink-weak); line-height: 2; }
</style>
