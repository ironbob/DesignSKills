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
  design_mode TEXT NOT NULL DEFAULT 'deliberate' CHECK (design_mode IN ('deliberate', 'rapid')),  -- deliberate=精细多候选（默认）；rapid=快速单候选+默认决策（质量 gate 不减）
  current_stage INTEGER NOT NULL DEFAULT 1,          -- 1..9
  stage_status TEXT NOT NULL DEFAULT '{"1":"ready"}', -- json：阶段号→ready/locked/running/awaiting_decision/failed/done
  contract_version INTEGER NOT NULL DEFAULT 1,        -- 契约版本（初始项目=1；每合并一个 revision +1）
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 任务（R7 全局串行）：一次有界 AI 调用 + L1 gate + L2 评审
-- revision_id 非空 = 增量任务（在 revisions/<id>/ 工作区执行，阶段图读写 revisions.stage_status）
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  revision_id INTEGER REFERENCES revisions(id) ON DELETE CASCADE,
  stage INTEGER NOT NULL,
  kind TEXT NOT NULL DEFAULT 'stage',                -- stage | retry
  state TEXT NOT NULL DEFAULT 'queued',              -- queued/running/gate_running/review_running/auto_redo/failed_needs_human/awaiting_decision/awaiting_acceptance/completed
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
  source TEXT NOT NULL DEFAULT 'form',                -- form | gallery | crit | rollback | defaults | ai_review | rapid_default | final_acceptance | revision_merge
  reason TEXT,
  revision_id INTEGER REFERENCES revisions(id) ON DELETE CASCADE,  -- 非空=revision 内拍板（页面范围可追溯）
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

-- 增量设计变更（已完成/进行中项目上的续作）：revision 在独立工作区执行，绝不写原项目与历史快照
CREATE TABLE IF NOT EXISTS revisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,                                -- 项目内序号（R1、R2…）
  title TEXT NOT NULL,
  requirement_text TEXT NOT NULL,                      -- 新需求正文
  doc_name TEXT,                                       -- 来源文件名（直接输入时 NULL）
  reason TEXT,                                         -- 变更说明
  base_snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),  -- 基于哪个已验收快照
  status TEXT NOT NULL DEFAULT 'analyzing',            -- analyzing/impact_ready/running/completed/merged/discarded
  change_levels TEXT NOT NULL DEFAULT '[]',            -- JSON：content/component/layout/style（确认范围时锁定）
  impact TEXT,                                         -- JSON：影响分析原始输出（AI）+ 确定性 plan
  version TEXT,                                        -- 合并后版本号（v2、v3…）
  stage_status TEXT NOT NULL DEFAULT '{"0":"ready"}',  -- json：revision 阶段图（0=影响分析 + 受影响阶段）
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  UNIQUE (project_id, seq)
);

-- 页面级模型：页面注册表（当前态 + 来源追溯）；历史快照与 revisions.impact 保留完整过程
CREATE TABLE IF NOT EXISTS pages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  page_id TEXT NOT NULL,                               -- S1、S5a…（与 03 屏幕盘点对齐）
  name TEXT NOT NULL,
  level TEXT,                                          -- IA 层级（从盘点表解析，缺省同 page_id）
  lifecycle TEXT NOT NULL DEFAULT 'initial',           -- initial/added/modified/removed（最后一次变更方式）
  status TEXT NOT NULL DEFAULT 'live',                 -- live/removed（removed=逻辑删除，行保留）
  origin_revision_id INTEGER REFERENCES revisions(id), -- 首次引入该页的 revision（NULL=初始项目）
  last_revision_id INTEGER REFERENCES revisions(id),   -- 最近一次修改该页的 revision（NULL=初始项目）
  created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
  UNIQUE (project_id, page_id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT
);
