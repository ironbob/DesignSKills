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
  current_stage INTEGER NOT NULL DEFAULT 1,          -- 1..9
  stage_status TEXT NOT NULL DEFAULT '{"1":"ready"}', -- json：阶段号→ready/locked/running/awaiting_decision/failed/done
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 任务（R7 全局串行）：一次有界 AI 调用 + gate
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage INTEGER NOT NULL,
  kind TEXT NOT NULL DEFAULT 'stage',                -- stage | retry
  state TEXT NOT NULL DEFAULT 'queued',              -- queued/running/gate_running/auto_redo/failed_needs_human/awaiting_decision/completed
  attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  gate_output TEXT,
  cost_s REAL,
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 决策台账（R3：全部拍板可审计可回放）
CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  stage INTEGER NOT NULL,
  question_id TEXT,                                   -- A-1 / P2-3 / snapshot-rollback …
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'form',                -- form | gallery | crit | rollback
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
