import { defineStore } from 'pinia'
import { api, type RevisionDetail, type RevisionDiff, type RevisionSummary, type SnapshotRow } from '@/api/client'
import { onEvent, type WbEvent } from '@/lib/sse'

export interface RevisionImpact {
  ready: boolean
  status?: string
  analysis?: Record<string, unknown>
  plan?: RevisionDetail['plan']
  locked?: boolean
  impact_md?: string | null
}

// 增量设计变更：revision 详情/影响分析/决策/合并 + 项目快照（查看/恢复）
export const useRevisionsStore = defineStore('revisions', {
  state: () => ({
    projectId: null as number | null,
    revision: null as RevisionDetail | null,
    list: [] as RevisionSummary[],
    impact: null as RevisionImpact | null,
    diff: null as RevisionDiff | null,
    snapshots: [] as SnapshotRow[],
    steps: [] as string[],
    error: '' as string,
    busy: false,
    _unsub: null as (() => void) | null,
  }),
  actions: {
    async load(projectId: number, revisionId: number) {
      this.projectId = projectId
      this.error = ''
      this.steps = []
      try {
        const [rev, list, impact, diff] = await Promise.all([
          api<RevisionDetail>(`/api/projects/${projectId}/revisions/${revisionId}`),
          api<RevisionSummary[]>(`/api/projects/${projectId}/revisions`),
          api<RevisionImpact>(`/api/projects/${projectId}/revisions/${revisionId}/impact`),
          api<RevisionDiff>(`/api/projects/${projectId}/revisions/${revisionId}/diff`),
        ])
        this.revision = rev
        this.list = list
        this.impact = impact
        this.diff = diff
        this.subscribe()
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      }
    },
    async refreshList() {
      if (!this.projectId) return
      try {
        this.list = await api<RevisionSummary[]>(`/api/projects/${this.projectId}/revisions`)
      } catch {
        /* 忽略：详情刷新会重试 */
      }
    },
    async refresh() {
      if (!this.projectId || !this.revision) return
      try {
        const [rev, impact, diff] = await Promise.all([
          api<RevisionDetail>(`/api/projects/${this.projectId}/revisions/${this.revision.id}`),
          api<RevisionImpact>(`/api/projects/${this.projectId}/revisions/${this.revision.id}/impact`),
          api<RevisionDiff>(`/api/projects/${this.projectId}/revisions/${this.revision.id}/diff`),
        ])
        this.revision = rev
        this.impact = impact
        this.diff = diff
      } catch {
        /* 事件风暴期刷新失败可忽略，下一事件会再刷 */
      }
    },
    subscribe() {
      if (this._unsub) this._unsub()
      this._unsub = onEvent((ev: WbEvent) => this.handleEvent(ev))
    },
    handleEvent(ev: WbEvent) {
      if (!this.revision || !this.projectId) return
      if (ev.project_id !== this.projectId) return
      if (ev.revision_id && ev.revision_id !== this.revision.id) return
      if (ev.type === 'revision_state') {
        if (ev.revision_id !== this.revision.id) return
        if (ev.detail) this.steps.push(ev.detail)
        void this.refresh()
        if (this.projectId) void this.refreshList()
        return
      }
      if (ev.revision_id !== this.revision.id) return
      if (ev.type === 'task_step' && ev.step) this.steps.push(ev.step)
      if (ev.type === 'task_state') {
        if (ev.detail) this.steps.push(ev.detail)
        if (ev.task_id && this.revision.current_task && ev.task_id === this.revision.current_task.id && ev.state) {
          this.revision.current_task.state = ev.state
        }
        void this.refresh()
      }
    },
    async confirmScope(reason: string) {
      if (!this.projectId || !this.revision) return
      this.busy = true
      try {
        await api(`/api/projects/${this.projectId}/revisions/${this.revision.id}/confirm`, {
          method: 'POST', body: JSON.stringify({ reason }),
        })
        await this.refresh()
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.busy = false
      }
    },
    async discard(reason: string) {
      if (!this.projectId || !this.revision) return
      this.busy = true
      try {
        await api(`/api/projects/${this.projectId}/revisions/${this.revision.id}/discard`, {
          method: 'POST', body: JSON.stringify({ reason }),
        })
        await this.refresh()
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.busy = false
      }
    },
    async startStage(stage: number) {
      if (!this.projectId || !this.revision) return
      this.steps = []
      try {
        await api(`/api/projects/${this.projectId}/revisions/${this.revision.id}/stages/${stage}/tasks`, { method: 'POST' })
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      }
    },
    async decide(stage: number, payload: Record<string, unknown>) {
      if (!this.projectId || !this.revision) return false
      this.busy = true
      try {
        await api(`/api/projects/${this.projectId}/revisions/${this.revision.id}/stages/${stage}/decision`, {
          method: 'POST', body: JSON.stringify(payload),
        })
        await this.refresh()
        return true
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
        return false
      } finally {
        this.busy = false
      }
    },
    async merge(reason: string) {
      if (!this.projectId || !this.revision) return
      this.busy = true
      try {
        await api(`/api/projects/${this.projectId}/revisions/${this.revision.id}/merge`, {
          method: 'POST', body: JSON.stringify({ reason }),
        })
        await this.refresh()
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.busy = false
      }
    },
    async loadSnapshots(projectId: number) {
      this.snapshots = await api<SnapshotRow[]>(`/api/projects/${projectId}/snapshots`)
    },
    async restoreSnapshot(projectId: number, seq: number, reason: string) {
      await api(`/api/projects/${projectId}/snapshots/${seq}/restore`, {
        method: 'POST', body: JSON.stringify({ reason }),
      })
      await this.loadSnapshots(projectId)
    },
  },
})
