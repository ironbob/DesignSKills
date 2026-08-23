-- AI 设计工作台 · sqlite schema（单用户本地；无 ORM，薄 db.py）
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  requirement_doc TEXT,                -- 原文件名（正文在工作区 requirement.md；项目内 00-requirement.md 为拷贝）
  requirement_updated_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('mobile_app', 'desktop_app', 'web')),
  canvas_w INTEGER NOT NULL,
  canvas_h INTEGER NOT NULL,
  run_mode TEXT NOT NULL DEFAULT 'step' CHECK (run_mode IN ('step', 'auto')),  -- step=每阶段人审；auto=事实类阶段过双层 gate 自动推进
  current_stage INTEGER NOT NULL DEFAULT 1,          -- 1..9
  stage_status TEXT NOT NULL DEFAULT '{"1":"ready"}', -- json：阶段号→ready/locked/running/awaiting_decision/failed/done
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 任务（R7 全局串行）：一次有界 AI 调用 + L1 gate + L2 评审
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage INTEGER NOT NULL,
  kind TEXT NOT NULL DEFAULT 'stage',                -- stage | retry
  state TEXT NOT NULL DEFAULT 'queued',              -- queued/running/gate_running/review_running/auto_redo/failed_needs_human/awaiting_decision/completed
  attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  gate_output TEXT,
  review_output TEXT,                                -- L2 findings JSON（reviews 表的冗余快照，任务页直读）
  cost_s REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- L2 评审记录（可审计可回放：每次评审一条；verdict 由引擎数出）
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  stage INTEGER NOT NULL,
  attempt INTEGER NOT NULL DEFAULT 1,
  verdict TEXT NOT NULL CHECK (verdict IN ('pass', 'redo')),  -- 🔴=0→pass；引擎判定，非评审器自报
  findings TEXT NOT NULL DEFAULT '[]',               -- JSON 数组：{id, criterion, severity(red|yellow), evidence, suggestion}
  red_count INTEGER NOT NULL DEFAULT 0,
  yellow_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 决策台账（R3：全部拍板可审计可回放；source=ai_review 即 auto 代批）
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage INTEGER NOT NULL,
  question_id TEXT,                                   -- A-1 / P2-3 / snapshot-rollback …
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'form',                -- form | gallery | crit | rollback | defaults | ai_review
  reason TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 快照（R6：阶段确认时刻的产物状态；回退不删历史）
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  stage INTEGER NOT NULL,
  reason TEXT,
  dir TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  UNIQUE (project_id, seq)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
