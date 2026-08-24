<script setup lang="ts">
// 修订视图：影响分析面板 + revision 阶段轨 + 增量任务/决策 + 基线↔revision 差异 + 合并/废弃
import { computed, onMounted, ref, watch } from 'vue'
import TopBar from '@/components/TopBar.vue'
import RevisionDecisionPanel from '@/components/RevisionDecisionPanel.vue'
import { useUiStore } from '@/stores/ui'
import { useRevisionsStore } from '@/stores/revisions'
import type { RevisionStatus } from '@/api/client'

const ui = useUiStore()
const rev = useRevisionsStore()
const panel = ref<InstanceType<typeof RevisionDecisionPanel> | null>(null)
const mergeReason = ref('')
const showSnapshots = ref(false)

onMounted(() => {
  if (ui.revisionProjectId != null && ui.revisionId != null) void rev.load(ui.revisionProjectId, ui.revisionId)
})

watch(
  () => rev.revision?.current_stage,
  (s) => {
    if (s && rev.revision?.stage_status[String(s)] === 'awaiting_decision') panel.value?.reload?.()
  },
)

const STATUS_META: Record<RevisionStatus, { t: string; cls: string }> = {
  analyzing: { t: '影响分析中（阶段 0）', cls: 'run' },
  impact_ready: { t: '影响分析就绪——待确认范围', cls: 'wait' },
  running: { t: '增量执行中（只重跑受影响阶段）', cls: 'run' },
  completed: { t: '受影响阶段全部完成——可合并', cls: 'wait' },
  merged: { t: '已合并入项目契约', cls: 'done' },
  discarded: { t: '已废弃（工作区保留可查）', cls: 'idle' },
}
const statusMeta = computed(() => (rev.revision ? STATUS_META[rev.revision.status] : STATUS_META.analyzing))

const LEVEL_LABEL: Record<string, string> = { content: '内容', component: '组件', layout: '布局', style: '风格' }

const stages = computed(() => {
  if (!rev.revision) return []
  return Object.entries(rev.revision.stage_status)
    .map(([k, v]) => ({ n: Number(k), name: rev.revision!.stage_names[k] ?? `阶段 ${k}`, state: v }))
    .sort((a, b) => a.n - b.n)
})

const analysis = computed(() => rev.impact?.analysis as any | undefined)
const plan = computed(() => (rev.impact?.locked ? rev.impact?.plan : rev.impact?.plan) as any | undefined)

const taskState = computed(() => rev.revision?.current_task?.state ?? '')
const canStartCurrent = computed(() => {
  const s = rev.revision?.stage_status[String(rev.revision?.current_stage)]
  return ['ready', 'failed_needs_human'].includes(s ?? '')
})
</script>

<template>
  <div class="page" v-if="rev.revision">
    <TopBar :crumb="`修订 R${rev.revision.seq}`"
            :crumb-dim="`${rev.revision.title} · 基线快照 #${rev.revision.base_snapshot_seq}${rev.revision.version ? ' · 已合并 ' + rev.revision.version : ''}`"
            heartbeat="idle" heartbeat-label="修订视图"
            @back="ui.backToProducts()" />
    <div class="body">
      <!-- 左：revision 阶段轨 -->
      <nav class="rail">
        <div class="railhead">增量阶段（R{{ rev.revision.seq }}）</div>
        <div v-for="s in stages" :key="s.n" class="stg" :class="{ done: s.state === 'done', cur: s.n === rev.revision!.current_stage && s.state !== 'done' }">
          <span class="n">{{ s.state === 'done' ? '✓' : s.n }}</span>
          <span class="nm">{{ s.name }}</span>
          <span v-if="s.state !== 'done'" class="flag">{{ s.state === 'ready' ? '未发起' : s.state === 'awaiting_decision' ? '▸ 待拍板' : s.state === 'failed_needs_human' ? '✕ 受阻' : '● 进行中' }}</span>
        </div>
        <div class="railfoot">
          <b>切换修订</b>
          <select :value="rev.revision.id" @change="ui.openRevision(rev.projectId!, Number(($event.target as HTMLSelectElement).value))">
            <option v-for="r in rev.list" :key="r.id" :value="r.id">R{{ r.seq }} · {{ r.title }}（{{ r.status }}）</option>
          </select>
        </div>
      </nav>

      <!-- 中：影响分析 + 差异 -->
      <div class="main">
        <div class="head">
          <h2>R{{ rev.revision.seq }} · {{ rev.revision.title }}<span class="st" :class="statusMeta.cls">{{ statusMeta.t }}</span></h2>
          <p class="meta">
            基线快照 #{{ rev.revision.base_snapshot_seq }} · 需求来源 {{ rev.revision.doc_name ?? '直接输入' }}
            <template v-if="rev.revision.reason"> · {{ rev.revision.reason }}</template>
          </p>
        </div>

        <div class="scroll">
          <!-- 影响分析 -->
          <section class="panel">
            <h3>影响分析（阶段 0）</h3>
            <p v-if="!rev.impact?.ready" class="empty">分析产出中——完成后此处展示结构化结果。</p>
            <template v-else>
              <p class="sum">{{ analysis?.summary }}</p>
              <div class="grid3">
                <div class="cell"><b>新增页面</b><span>{{ plan?.pages?.added?.length ? plan.pages.added.join('、') : '无' }}</span></div>
                <div class="cell"><b>修改页面</b><span>{{ plan?.pages?.modified?.length ? plan.pages.modified.join('、') : '无' }}</span></div>
                <div class="cell"><b>删除页面</b><span>{{ plan?.pages?.removed?.length ? plan.pages.removed.join('、') : '无' }}</span></div>
                <div class="cell"><b>变更级别</b><span>{{ plan?.change_levels?.length ? plan.change_levels.map((l: string) => LEVEL_LABEL[l] ?? l).join('、') : '—' }}</span></div>
                <div class="cell"><b>重跑阶段</b><span>{{ plan?.stages_to_rerun?.join(' / ') ?? '—' }}{{ rev.impact?.locked ? '' : '（待确认锁定）' }}</span></div>
                <div class="cell"><b>回归验证（无需重做）</b><span>{{ plan?.regression_pages?.length ? plan.regression_pages.join('、') : '无' }}</span></div>
              </div>
              <ul v-if="plan?.rationale?.length" class="why">
                <li v-for="(r, i) in plan.rationale" :key="i">{{ r }}</li>
              </ul>
              <div v-if="analysis?.navigation?.length || analysis?.flows?.length" class="cross">
                <b>交叉影响：</b>{{ [...(analysis.flows ?? []), ...(analysis.navigation ?? [])].join('；') }}
              </div>
              <a class="md" v-if="rev.impact?.impact_md"
                 :href="`/api/preview/${rev.projectId}/revisions/${rev.revision.id}/00-impact.md`" target="_blank">查看完整影响分析 →</a>
            </template>
          </section>

          <!-- 差异 -->
          <section class="panel">
            <h3>基线 ↔ 当前修订差异</h3>
            <div v-if="rev.diff" class="diffs">
              <div class="cell add"><b>新增 {{ rev.diff.added.length }}</b><span>{{ rev.diff.added.join('、') || '无' }}</span></div>
              <div class="cell chg"><b>变更 {{ rev.diff.changed.length }}</b><span>{{ rev.diff.changed.join('、') || '无' }}</span></div>
              <div class="cell rm"><b>删除 {{ rev.diff.removed.length }}</b><span>{{ rev.diff.removed.join('、') || '无' }}</span></div>
            </div>
            <p class="meta">未变更产物 {{ rev.diff?.unchanged_count ?? 0 }} 件 · 继承基线不重做</p>
            <div class="arts" v-if="rev.revision.artifacts.length">
              <a v-for="a in rev.revision.artifacts.slice(0, 14)" :key="a.path"
                 :href="`/api/preview/${rev.projectId}/revisions/${rev.revision.id}/${a.path}`" target="_blank">{{ a.path }}</a>
            </div>
          </section>

          <!-- 过程步骤 -->
          <section class="panel" v-if="rev.steps.length">
            <h3>过程</h3>
            <div class="steps">
              <div v-for="(s, i) in rev.steps.slice(-14)" :key="i">{{ s }}</div>
            </div>
          </section>
        </div>
      </div>

      <!-- 右：操作 -->
      <div class="ops">
        <div class="card">
          <h4>当前任务</h4>
          <p class="kv">阶段 {{ rev.revision.current_stage }} · {{ rev.revision.stage_names[String(rev.revision.current_stage)] ?? '' }}</p>
          <p class="kv">状态 {{ taskState || '—' }}</p>
          <p v-if="rev.revision.current_task?.error" class="err">{{ rev.revision.current_task.error }}</p>
          <button v-if="canStartCurrent" class="primary" @click="rev.startStage(rev.revision!.current_stage)">
            {{ rev.revision.stage_status[String(rev.revision.current_stage)] === 'failed_needs_human' ? '重试阶段' : '发起阶段任务' }}
          </button>
        </div>

        <RevisionDecisionPanel ref="panel" v-if="rev.revision.stage_status[String(rev.revision.current_stage)] === 'awaiting_decision' && rev.revision.status === 'running'" />

        <div class="card" v-if="rev.revision.status === 'impact_ready'">
          <h4>确认范围</h4>
          <p class="hint">确认后只解锁受影响阶段，原项目与历史快照不被改动。</p>
          <button class="primary" :disabled="rev.busy" @click="rev.confirmScope('界面确认范围')">确认范围并启动增量</button>
          <button class="ghost" :disabled="rev.busy" @click="rev.discard('范围不认可')">废弃此修订</button>
        </div>

        <div class="card" v-if="rev.revision.status === 'completed'">
          <h4>合并回项目</h4>
          <p class="hint">生成新完整契约（09-spec + 06-tokens + 07-hifi，含基线/变更摘要/受影响页面/回归结果/版本号），合并前先落项目快照。</p>
          <input v-model="mergeReason" placeholder="合并说明（可选）" />
          <button class="primary" :disabled="rev.busy" @click="rev.merge(mergeReason)">合并为新版本</button>
        </div>

        <div class="card" v-if="rev.revision.status === 'merged'">
          <h4>已合并 {{ rev.revision.version }}</h4>
          <p class="hint">项目契约已更新，历史快照保留基线，可随时对比或恢复。</p>
        </div>

        <div class="card">
          <h4>项目快照</h4>
          <button class="ghost" @click="showSnapshots = !showSnapshots; if (showSnapshots && rev.projectId) rev.loadSnapshots(rev.projectId)">
            {{ showSnapshots ? '收起' : '查看快照历史' }}
          </button>
          <div v-if="showSnapshots" class="snaps">
            <div v-for="s in rev.snapshots" :key="s.seq" class="snap">
              <span>#{{ s.seq }} · 阶段{{ s.stage }}</span>
              <span class="rs">{{ s.reason }}</span>
              <a v-if="rev.projectId" :href="`/api/projects/${rev.projectId}/snapshots/${s.seq}/file?path=09-spec.md`" target="_blank">spec</a>
              <button class="restore" @click="rev.projectId && rev.restoreSnapshot(rev.projectId, s.seq, '界面恢复')">恢复</button>
            </div>
          </div>
          <p class="hint">恢复 = 项目工作区还原为该快照（先自动保全当前状态为最新快照；历史快照本体只读）。</p>
        </div>
        <p v-if="rev.error" class="err">{{ rev.error }}</p>
      </div>
    </div>
  </div>
  <div v-else class="page"><div class="loading">{{ rev.error ? `加载失败：${rev.error}` : '加载中…' }}</div></div>
</template>

<style scoped>
.page { height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.loading { flex: 1; display: flex; align-items: center; justify-content: center; color: var(--ink-weak); }
.body { flex: 1; display: flex; min-height: 0; }
.rail { flex: 0 0 208px; border-right: 1px solid var(--line); display: flex; flex-direction: column; background: var(--surface); overflow-y: auto; }
.railhead { padding: 14px 14px 8px; font-size: 11px; color: var(--ink-weak); font-weight: 700; letter-spacing: 0.05em; }
.stg { display: flex; align-items: center; gap: 9px; padding: 8px 12px 8px 11px; font-size: var(--fs-ui); border-left: 3px solid transparent; color: var(--ink-weak); }
.stg .n { width: 20px; height: 20px; flex: 0 0 20px; border: 1px solid #c7cbd3; border-radius: 50%; text-align: center; line-height: 20px; font-size: 10px; }
.stg.done { color: #374151; }
.stg.done .n { background: var(--ink); color: #fff; border-color: var(--ink); }
.stg.cur { background: #fff; border-left-color: var(--accent); color: var(--ink); font-weight: 700; }
.stg.cur .n { border-color: var(--accent); color: var(--accent); }
.flag { margin-left: auto; font-size: 10px; color: #9ca3af; }
.railfoot { margin-top: auto; border-top: 1px solid var(--line); padding: 10px 12px; font-size: 11px; color: var(--ink-weak); display: flex; flex-direction: column; gap: 6px; }
.railfoot b { color: #374151; }
.railfoot select { border: 1px solid var(--line); border-radius: var(--r-small); padding: 5px; font-size: 11px; background: #fff; max-width: 180px; }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; background: #fff; }
.head { padding: 16px 24px 12px; border-bottom: 1px solid var(--line); }
.head h2 { margin: 0; font-size: var(--fs-title); font-weight: 800; display: flex; align-items: center; gap: 12px; }
.st { font-size: 11px; padding: 3px 9px; border-radius: 999px; border: 1px solid var(--line); font-weight: 600; }
.st.run { color: var(--accent); border-color: var(--accent); }
.st.wait { color: var(--sem-warn); border-color: var(--sem-warn); }
.st.done { color: #374151; }
.st.idle { color: var(--ink-weak); }
.meta { margin: 4px 0 0; font-size: var(--fs-caption); color: var(--ink-weak); }
.scroll { flex: 1; overflow-y: auto; padding: 18px 24px; display: flex; flex-direction: column; gap: 16px; }
.panel { border: 1px solid var(--line); border-radius: var(--r-card); padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
.panel h3 { margin: 0; font-size: 13px; font-weight: 800; }
.empty { margin: 0; color: var(--ink-weak); font-size: var(--fs-caption); }
.sum { margin: 0; font-size: var(--fs-body); line-height: 1.7; }
.grid3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.cell { border: 1px solid var(--line); border-radius: var(--r-small); padding: 8px 10px; display: flex; flex-direction: column; gap: 4px; font-size: 11px; min-width: 0; }
.cell b { color: var(--ink-weak); font-weight: 700; }
.cell span { font-size: var(--fs-ui); color: #111827; word-break: break-all; }
.why { margin: 0; padding-left: 18px; font-size: var(--fs-caption); color: var(--ink-weak); line-height: 1.9; }
.cross { font-size: var(--fs-caption); color: #374151; background: var(--surface); border-radius: var(--r-small); padding: 7px 10px; }
.md { font-size: 12px; color: var(--accent); }
.diffs { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.cell.add span { color: #059669; }
.cell.chg span { color: var(--accent); }
.cell.rm span { color: var(--danger); }
.arts { display: flex; flex-wrap: wrap; gap: 6px; }
.arts a { font-size: 11px; color: #4b5563; border: 1px solid var(--line); border-radius: 5px; padding: 3px 7px; text-decoration: none; }
.steps { font-size: 11px; color: var(--ink-weak); line-height: 1.9; max-height: 180px; overflow-y: auto; }
.ops { flex: 0 0 var(--ops-w); border-left: 1px solid var(--line); display: flex; flex-direction: column; gap: 14px; padding: var(--sp-3); box-sizing: border-box; overflow-y: auto; background: #fff; }
.card { border: 1px solid var(--line); border-radius: var(--r-card); background: #fff; padding: 13px 15px; display: flex; flex-direction: column; gap: 9px; }
.card h4 { margin: 0; font-size: 11px; color: var(--ink-weak); font-weight: 700; letter-spacing: 0.03em; }
.kv { margin: 0; font-size: var(--fs-caption); color: #374151; }
.hint { margin: 0; font-size: var(--fs-caption); color: var(--ink-weak); line-height: 1.7; }
.err { margin: 0; font-size: 12px; color: var(--danger); }
input { border: 1px solid var(--line); border-radius: var(--r-small); padding: 7px 9px; font-size: var(--fs-ui); }
.primary { background: var(--accent); color: #fff; border: none; border-radius: var(--r-small); padding: 9px 14px; font-weight: 700; cursor: pointer; }
.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.ghost { border: 1px solid #c7cbd3; background: #fff; border-radius: var(--r-small); padding: 8px 12px; cursor: pointer; }
.snaps { display: flex; flex-direction: column; gap: 5px; max-height: 220px; overflow-y: auto; }
.snap { display: flex; align-items: center; gap: 7px; font-size: 11px; border-bottom: 1px dashed var(--line); padding-bottom: 4px; }
.snap .rs { flex: 1; color: var(--ink-weak); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.snap a { color: var(--accent); }
.restore { border: 1px solid #c7cbd3; background: #fff; border-radius: 4px; padding: 2px 7px; font-size: 11px; cursor: pointer; }
</style>
