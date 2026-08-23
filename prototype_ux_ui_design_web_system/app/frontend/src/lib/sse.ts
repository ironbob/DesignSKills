// 全局 SSE 单例（/api/events）：事件驱动，无轮询（09-spec「等待可离开」）
export interface ReviewFinding {
  id: string
  criterion: string
  severity: 'red' | 'yellow'
  evidence: string
  suggestion?: string
}

export interface WbEvent {
  type: 'task_state' | 'task_step' | 'artifact_increment' | 'gate_result' | 'review_result' | 'heartbeat'
  ts: number
  project_id?: number
  task_id?: number
  stage?: number
  state?: string
  detail?: string
  step?: string
  path?: string
  ok?: boolean
  problems?: string[]
  red?: number
  yellow?: number
  findings?: ReviewFinding[]
}

type Handler = (e: WbEvent) => void
const handlers = new Set<Handler>()
let es: EventSource | null = null

export function connectSSE(): void {
  if (es) return
  es = new EventSource('/api/events')
  es.onmessage = (m) => {
    let ev: WbEvent
    try {
      ev = JSON.parse(m.data) as WbEvent
    } catch {
      return
    }
    for (const h of handlers) h(ev)
  }
  es.onerror = () => {
    // EventSource 自动重连；重连后服务端 replay 会补齐断线期事件
  }
}

export function onEvent(h: Handler): () => void {
  handlers.add(h)
  return () => handlers.delete(h)
}
