<script setup lang="ts">
// 增量需求创建浮层：标题 + 需求正文（输入或上传 .md/.txt）+ 变更说明 + 基线快照（默认最新）
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useUiStore } from '@/stores/ui'
import type { RevisionDetail, SnapshotRow } from '@/api/client'

const ui = useUiStore()
const title = ref('')
const requirementText = ref('')
const docName = ref('')
const reason = ref('')
const snapshots = ref<SnapshotRow[]>([])
const baseSnapshotSeq = ref<number | null>(null)
const submitting = ref(false)
const error = ref('')

async function onFile(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0]
  if (!f) return
  docName.value = f.name
  requirementText.value = await f.text()
  if (!title.value) title.value = f.name.replace(/\.(md|txt|markdown)$/i, '')
}

async function submit() {
  if (!ui.revisionWizard || !title.value.trim() || !requirementText.value.trim()) {
    error.value = '标题与需求正文必填'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    const snap = snapshots.value.find((s) => s.seq === baseSnapshotSeq.value)
    const latest = snapshots.value[snapshots.value.length - 1]
    const rev = await api<RevisionDetail>(`/api/projects/${ui.revisionWizard.projectId}/revisions`, {
      method: 'POST',
      body: JSON.stringify({
        title: title.value,
        requirement_text: requirementText.value,
        doc_name: docName.value || null,
        reason: reason.value,
        // 只在用户显式选了非最新快照时传 id；后端默认取最新已确认快照
        ...(snap && snap.seq !== latest.seq ? { base_snapshot_id: snap.id } : {}),
      }),
    })
    ui.openRevision(ui.revisionWizard.projectId, rev.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  if (!ui.revisionWizard) return
  try {
    snapshots.value = await api<SnapshotRow[]>(`/api/projects/${ui.revisionWizard.projectId}/snapshots`)
    baseSnapshotSeq.value = snapshots.value.length ? snapshots.value[snapshots.value.length - 1].seq : null
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})
</script>

<template>
  <div class="mask" @click.self="ui.revisionWizard = null">
    <div class="modal">
      <h3>新增需求 · 创建设计变更</h3>
      <p class="sub">
        在「{{ ui.revisionWizard?.projectName }}」的已验收基线上提交增量需求。创建后先跑<b>影响分析</b>（阶段 0），
        确认范围后只重跑受影响阶段——原版本与历史快照不会被覆盖。
      </p>
      <label>变更标题 *
        <input v-model="title" placeholder="如：打卡日历支持补签" />
      </label>
      <label>需求正文 *（粘贴或上传文件）
        <div class="row">
          <input v-model="docName" placeholder="来源文件名（可空）" />
          <label class="upl">上传 .md / .txt<input type="file" accept=".md,.txt,.markdown" @change="onFile" /></label>
        </div>
        <textarea v-model="requirementText" rows="7" placeholder="# 增量需求&#10;用户场景、规则、验收点…" />
      </label>
      <label>变更说明（为什么改）
        <input v-model="reason" placeholder="如：运营活动需要成就入口" />
      </label>
      <label>基线快照
        <select v-model.number="baseSnapshotSeq">
          <option v-for="s in snapshots" :key="s.seq" :value="s.seq">
            #{{ s.seq }} · 阶段 {{ s.stage }} · {{ s.reason ?? '' }}
          </option>
        </select>
      </label>
      <p v-if="!snapshots.length" class="warn">该项目还没有已确认快照——先在主流程完成至少一个阶段决策。</p>
      <p v-if="error" class="err">{{ error }}</p>
      <div class="btns">
        <button class="ghost" @click="ui.revisionWizard = null">取消</button>
        <button class="primary" :disabled="submitting || !snapshots.length" @click="submit">
          {{ submitting ? '创建中…' : '创建并跑影响分析' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask { position: fixed; inset: 0; background: rgba(17, 24, 39, 0.45); display: flex; align-items: center; justify-content: center; z-index: 50; }
.modal {
  width: 560px; max-height: 86vh; overflow-y: auto;
  background: #fff; border-radius: var(--r-panel); padding: 22px 26px;
  display: flex; flex-direction: column; gap: 13px;
}
h3 { margin: 0; font-size: 17px; font-weight: 800; }
.sub { margin: 0; font-size: var(--fs-caption); color: var(--ink-weak); line-height: 1.8; }
.sub b { color: #374151; }
label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: #4b5563; font-weight: 600; }
input, textarea, select {
  border: 1px solid var(--line); border-radius: var(--r-small); padding: 8px 10px;
  font-size: var(--fs-ui); font-family: inherit; background: #fff;
}
textarea { font-family: ui-monospace, monospace; font-size: 12px; }
.row { display: flex; gap: 8px; }
.row input { flex: 1; }
.upl { position: relative; overflow: hidden; border: 1px solid var(--line); border-radius: var(--r-small); padding: 8px 12px; background: var(--surface); cursor: pointer; font-weight: 600; }
.upl input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.warn { margin: 0; font-size: 12px; color: var(--sem-warn); }
.err { margin: 0; font-size: 12px; color: var(--danger); }
.btns { display: flex; justify-content: flex-end; gap: 10px; margin-top: 4px; }
.primary { background: var(--accent); color: #fff; border: none; border-radius: var(--r-small); padding: 9px 18px; font-weight: 700; cursor: pointer; }
.primary:disabled { opacity: 0.5; cursor: not-allowed; }
.ghost { border: 1px solid #c7cbd3; background: #fff; border-radius: var(--r-small); padding: 9px 16px; cursor: pointer; }
</style>
