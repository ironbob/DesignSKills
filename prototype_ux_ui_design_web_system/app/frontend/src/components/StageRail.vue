<script setup lang="ts">
// 左阶段轨（208px · P3-1）：done=已确认可回退（M1-4 接回退）/ cur=当前（子状态旗标）/ 未到=弱墨
import { useWorkbenchStore } from '@/stores/workbench'

const wb = useWorkbenchStore()

function statusOf(n: number): string {
  if (!wb.project) return 'locked'
  if (n < wb.project.current_stage) return 'done'
  if (n === wb.project.current_stage) return 'cur'
  return 'locked'
}

const SUB_FLAGS: Record<string, string> = {
  ready: '未发起',
  running: '● 进行中',
  auto_redo: '● 自动重做',
  gate_running: '● gate 校验',
  review_running: '● L2 评审',
  awaiting_decision: '▸ 待拍板',
  awaiting_acceptance: '▸ 待验收',
  failed_needs_human: '✕ 受阻',
}
</script>

<template>
  <nav class="rail" v-if="wb.project">
    <div class="railhead">九阶段</div>
    <div
      v-for="(name, i) in wb.project.stage_names"
      :key="name"
      class="stg"
      :class="statusOf(i + 1)"
    >
      <span class="n">{{ statusOf(i + 1) === 'done' ? '✓' : i + 1 }}</span>
      <span class="nm">{{ name }}</span>
      <span v-if="statusOf(i + 1) === 'done'" class="flag">可回退</span>
      <span v-else-if="statusOf(i + 1) === 'cur'" class="flag" :data-s="wb.stageState">{{ SUB_FLAGS[wb.stageState] ?? '' }}</span>
    </div>
    <div class="railfoot">
      <b>历史</b>：台账 · 快照<br />
      <b>修改产物</b> · 回退阶段
    </div>
  </nav>
</template>

<style scoped>
.rail {
  flex: 0 0 var(--rail-w);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  background: var(--surface);
  overflow-y: auto;
}
.railhead { padding: 14px 14px 8px; font-size: 11px; color: var(--ink-weak); font-weight: 700; letter-spacing: 0.05em; }
.stg {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 14px 9px 11px;
  font-size: var(--fs-ui);
  border-left: 3px solid transparent;
  color: var(--ink-weak);
}
.stg .n {
  width: 21px; height: 21px; flex: 0 0 21px;
  border: 1px solid #c7cbd3; border-radius: 50%;
  text-align: center; line-height: 21px; font-size: 11px;
}
.stg.done { color: #374151; }
.stg.done .n { background: var(--ink); color: #fff; border-color: var(--ink); }
.stg.cur { background: #fff; border-left-color: var(--accent); color: var(--ink); font-weight: 700; }
.stg.cur .n { border-color: var(--accent); color: var(--accent); }
.flag { margin-left: auto; font-size: 10px; color: #9ca3af; }
.flag[data-s='awaiting_decision'] { color: var(--sem-warn); font-weight: 700; }
.flag[data-s='failed_needs_human'] { color: var(--danger); font-weight: 700; }
.flag[data-s='running'], .flag[data-s='auto_redo'], .flag[data-s='gate_running'] { color: var(--accent); font-weight: 700; }
.railfoot { margin-top: auto; border-top: 1px solid var(--line); padding: 12px 14px; font-size: var(--fs-caption); color: var(--ink-weak); line-height: 2; }
.railfoot b { color: #374151; font-weight: 600; }
</style>
