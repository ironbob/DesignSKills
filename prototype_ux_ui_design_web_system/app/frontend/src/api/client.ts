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
}

export interface Product {
  id: number
  name: string
  requirement_doc: string | null
  requirement_updated_at: string | null
  projects: Project[]
  updated_at: string
}

export const PLATFORM_PRESETS: Record<Platform, { label: string; width: number; height: number }> = {
  mobile_app: { label: '手机App', width: 390, height: 844 },
  desktop_app: { label: '桌面App', width: 1280, height: 800 },
  web: { label: 'Web系统', width: 1440, height: 900 },
}
