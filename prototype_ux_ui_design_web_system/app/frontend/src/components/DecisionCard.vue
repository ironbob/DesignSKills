<script setup lang="ts">
// 决策卡（右栏第二张）：stage ready=引导语；running=免打扰；awaiting=唯一实心主键；failed=失败卡
import { computed } from 'vue'
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()

// 按当前阶段决策类型出按钮文案（decision_types 由项目详情返回）
const DECIDE_TEXT: Record<string, string> = {
  question_form: '打开问题单 · 逐题拍板',
  gallery: '挑变体/方向 · 拍板',
  crit: '审 crit 处置 · 拍板',
  confirm: '确认走向 · 进下一阶段',
}
const decideText = computed(() => {
  const stage = wb.project?.current_stage
  const t = stage ? wb.project?.decision_types[String(stage)] : undefined
  const rapid = wb.project?.design_mode === 'rapid'
  if (stage === 4) return rapid ? '确认默认结构方案 · 继续快速执行' : '挑线框变体 · 拍板'
  if (stage === 5) return rapid ? '确认默认视觉方向 · 继续快速执行' : '挑视觉方向 · 拍板'
  if (stage === 8) return '审 crit 处置 · 拍板'
  return rapid && t === 'confirm' ? '继续快速执行 · 进下一阶段' : (DECIDE_TEXT[t ?? 'confirm'] ?? '确认走向 · 进下一阶段')
})
</script>

<template>
  <div v-if="wb.project">
    <!-- 失败卡（单屏级不锁阶段：失败三要素） -->
    <div v-if="wb.stageState === 'failed_needs_human' && wb.project.current_task" class="failcard">
      <h4><span class="x">✕</span>阶段 {{ wb.project.current_stage }} · 生成失败</h4>
      <p>{{ wb.project.current_task.error || '未知原因' }}</p>
      <p>共享重试预算（L1/L2 打回合计 2 次）已用尽。失败无损：已产出文件不受影响。</p>
      <button class="primary" @click="wb.startStage(wb.project.current_stage)">手动重试</button>
    </div>

    <!-- 决策卡 -->
    <div v-else class="deci" :data-live="wb.stageState === 'awaiting_decision'">
      <div class="k">当前决策 · 阶段 {{ wb.project.current_stage }} · {{ wb.project.stage_names[wb.project.current_stage - 1] }}</div>
      <div v-if="wb.stageState === 'awaiting_decision'" class="q">
        gate 已过——{{ wb.project.current_stage === 1 ? '设计前提问题等你逐题拍板' : '产物等你确认走向' }}
      </div>
      <div v-else-if="wb.stageState === 'awaiting_acceptance'" class="q">
        九阶段完成——最终规格、关键默认决策、未决 U-x 与 🟡 处置待你一次验收
      </div>
      <div v-else class="q muted">{{ wb.stageState === 'ready' ? '发起任务后，产物与决策点会出现在这里' : '任务执行中——先出产物，过 gate 后决策点亮' }}</div>
      <button
        v-if="wb.stageState === 'awaiting_decision'"
        class="primary"
        @click="wb.openQuestion()"
      >
        {{ decideText }}
      </button>
      <button
        v-else-if="wb.stageState === 'awaiting_acceptance'"
        class="primary"
        @click="wb.openAcceptance()"
      >
        打开最终验收 · 导出确认
      </button>
    </div>
  </div>
</template>

<style scoped>
.deci { border: 1px solid var(--line); border-radius: var(--r-card); background: #fff; padding: 13px 15px; }
.deci[data-live='true'] { border: 1.5px solid var(--accent); background: var(--surface); }
.k { font-size: 11px; color: var(--ink-weak); font-weight: 700; letter-spacing: 0.03em; }
.deci[data-live='true'] .k { color: var(--accent); }
.q { font-size: 15px; font-weight: 700; margin: 7px 0 4px; line-height: 1.5; }
.q.muted { font-size: var(--fs-ui); color: var(--ink-weak); font-weight: 400; line-height: 1.7; margin: 10px 0; }
.primary {
  display: block;
  width: 100%;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: var(--r-small);
  padding: 11px 0;
  font-size: var(--fs-ui);
  font-weight: 700;
  margin-top: 10px;
  cursor: pointer;
}
.failcard { border: 1.5px solid var(--danger); border-radius: var(--r-card); background: #fff; padding: 13px 15px; }
.failcard h4 { margin: 0 0 7px; font-size: var(--fs-ui); color: var(--danger); font-weight: 700; }
.failcard .x { margin-right: 6px; }
.failcard p { font-size: var(--fs-caption); color: #4b5563; margin: 0 0 5px; line-height: 1.7; }
</style>
