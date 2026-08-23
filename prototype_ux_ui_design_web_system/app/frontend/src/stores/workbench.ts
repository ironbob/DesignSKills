import { defineStore } from 'pinia'
import { api } from '@/api/client'
import { onEvent, type ReviewFinding, type WbEvent } from '@/lib/sse'

export interface Artifact {
  path: string
  kind: 'md' | 'html' | 'json'
  mtime: number
}

export interface TaskRow {
  id: number
  project_id: number
  stage: number
  state: string
  attempts: number
  error: string | null
  gate_output: string | null
  review_output: string | null
  cost_s: number | null
}

export interface DecisionMeta {
  category: 'answer' | 'fact' | 'taste' | 'exemption'
  label: string
  human_decision: boolean
}

export interface ProjectDetail {
  id: number
  product_id: number
  product_name: string
  name: string
  platform: string
  platform_label: string
  canvas: { width: number; height: number }
  run_mode: 'step' | 'auto'
  current_stage: number
  stage_status: Record<string, string>
  decision_meta: Record<string, DecisionMeta>
  updated_at: string
  artifacts: Artifact[]
  stage_names: string[]
  current_task: TaskRow | null
}

export const useWorkbenchStore = defineStore('workbench', {
  state: () => ({
    project: null as ProjectDetail | null,
    loading: false,
    error: '' as string,
    steps: [] as string[], // 当前任务步骤（标题级，P2-2）
    increments: [] as string[], // 产物增量（新→旧）
    reviewFindings: [] as ReviewFinding[], // L2 评审 findings（最新一次）
    questionOpen: false, // S5a 问题单浮层
    _unsub: null as (() => void) | null,
  }),
  getters: {
    stageState(state): string {
      if (!state.project) return 'locked'
      return state.project.stage_status[String(state.project.current_stage)] ?? 'locked'
    },
  },
  actions: {
    async load(projectId: number) {
      this.loading = true
      this.error = ''
      this.steps = []
      this.increments = []
      this.reviewFindings = []
      try {
        this.project = await api<ProjectDetail>(`/api/projects/${projectId}`)
        if (this.project.current_task && this.project.current_task.state !== 'completed') {
          this.steps.push(`任务状态：${this.project.current_task.state}`)
        }
        this.subscribe()
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      } finally {
        this.loading = false
      }
    },
    subscribe() {
      if (this._unsub) this._unsub()
      this._unsub = onEvent((ev: WbEvent) => this.handleEvent(ev))
    },
    handleEvent(ev: WbEvent) {
      if (!this.project || ev.project_id !== this.project.id) return
      const st = this.project.stage_status
      if (ev.type === 'task_step' && ev.step) {
        this.steps.push(ev.step)
      } else if (ev.type === 'artifact_increment' && ev.path) {
        this.increments.unshift(ev.path)
      } else if (ev.type === 'task_state') {
        if (ev.stage) st[String(ev.stage)] = ev.state ?? st[String(ev.stage)]
        if (ev.detail) this.steps.push(ev.detail)
        if (this.project.current_task && ev.task_id === this.project.current_task.id) {
          this.project.current_task.state = ev.state ?? this.project.current_task.state
        } else {
          this.project.current_task = {
            id: ev.task_id ?? 0,
            project_id: this.project.id,
            stage: ev.stage ?? this.project.current_stage,
            state: ev.state ?? 'queued',
            attempts: 1,
            error: null,
            gate_output: null,
            review_output: null,
            cost_s: null,
          }
        }
        if (ev.state === 'running') void this.refreshArtifacts()
      } else if (ev.type === 'review_result') {
        this.reviewFindings = ev.findings ?? []
      }
      if (ev.type === 'artifact_increment') {
        if (!this.project.artifacts.some((a) => a.path === ev.path)) {
          this.project.artifacts.push({
            path: ev.path!,
            kind: (ev.path!.endsWith('.html') ? 'html' : ev.path!.endsWith('.json') ? 'json' : 'md') as Artifact['kind'],
            mtime: Date.now() / 1000,
          })
        }
      }
    },
    async refreshArtifacts() {
      if (!this.project) return
      const fresh = await api<ProjectDetail>(`/api/projects/${this.project.id}`)
      this.project.artifacts = fresh.artifacts
    },
    async startStage(stage: number) {
      if (!this.project) return
      this.steps = []
      this.increments = []
      this.reviewFindings = []
      try {
        await api(`/api/projects/${this.project.id}/stages/${stage}/tasks`, { method: 'POST' })
      } catch (e) {
        this.error = e instanceof Error ? e.message : String(e)
      }
    },
    openQuestion() {
      this.questionOpen = true
    },
  },
})
