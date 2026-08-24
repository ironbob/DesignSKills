// 极简 API 客户端（同源 /api，开发期经 vite proxy）
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = `${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* keep status */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

/* ---------- 类型（与 backend schema 对齐） ---------- */

export type Platform = 'mobile_app' | 'desktop_app' | 'web'

export interface Project {
  id: number
  name: string
  platform: Platform
  canvas: { width: number; height: number }
  run_mode: 'step' | 'auto'
  design_mode: 'deliberate' | 'rapid'
  current_stage: number
  stage_status: Record<string, string> // 阶段号 → locked/current/awaiting_decision/done/failed...
  requirement_doc: string | null
  updated_at: string
  contract_version: number
  snapshot_count: number
  revisions: RevisionSummary[]
}

export interface Product {
  id: number
  name: string
  requirement_doc: string | null
  requirement_updated_at: string | null
  projects: Project[]
  updated_at: string
}

/* ---------- 增量设计变更（revision）---------- */

export type RevisionStatus = 'analyzing' | 'impact_ready' | 'running' | 'completed' | 'merged' | 'discarded'
export type ChangeLevel = 'content' | 'component' | 'layout' | 'style'

export interface RevisionSummary {
  id: number
  seq: number
  title: string
  status: RevisionStatus
  version: string | null
  updated_at: string
}

export interface RevisionPlan {
  change_levels: ChangeLevel[]
  pages: { added: string[]; modified: string[]; removed: string[] }
  stages_to_rerun: number[]
  regression_pages: string[]
  rationale: string[]
}

export interface RevisionDetail {
  id: number
  project_id: number
  seq: number
  title: string
  doc_name: string | null
  reason: string | null
  base_snapshot_id: number
  base_snapshot_seq: number | string
  status: RevisionStatus
  change_levels: ChangeLevel[]
  version: string | null
  stage_status: Record<string, string>
  stage_names: Record<string, string>
  created_at: string
  updated_at: string
  current_stage: number
  current_task: TaskRow | null
  impact: Record<string, unknown> | null
  plan: RevisionPlan | null
  tasks: TaskRow[]
  decisions: Record<string, unknown>[]
  artifacts: { path: string; kind: string; mtime: number }[]
}

export interface RevisionDiff {
  added: string[]
  changed: string[]
  removed: string[]
  unchanged_count: number
  pages: { added?: string[]; modified?: string[]; removed?: string[] }
  base_snapshot_seq: number | string
}

export interface SnapshotRow {
  id: number
  seq: number
  stage: number
  reason: string | null
  created_at: string
  base_of_revisions?: number
}

export const PLATFORM_PRESETS: Record<Platform, { label: string; width: number; height: number }> = {
  mobile_app: { label: '手机App', width: 390, height: 844 },
  desktop_app: { label: '桌面App', width: 1280, height: 800 },
  web: { label: 'Web系统', width: 1440, height: 900 },
}

export interface TaskRow {
  id: number
  project_id: number
  revision_id?: number | null
  stage: number
  state: string
  attempts: number
  error: string | null
  gate_output: string | null
  review_output: string | null
  cost_s: number | null
}
