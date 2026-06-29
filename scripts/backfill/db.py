"""
SQLite 数据库管理 — 历史回填所有状态。
可重复初始化，不丢失已有数据。
"""

import sqlite3
import os
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA = """
-- 来源盘点状态
CREATE TABLE IF NOT EXISTS sources (
    source_id      TEXT PRIMARY KEY,
    platform       TEXT NOT NULL,
    category       TEXT NOT NULL,
    name           TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending',
    items_in_range INTEGER DEFAULT 0,
    pages_fetched  INTEGER DEFAULT 0,
    oldest_seen    TEXT,
    newest_seen    TEXT,
    stop_reason    TEXT,
    error_message  TEXT,
    updated_at     TEXT DEFAULT (datetime('now'))
);

-- 节目总清单
CREATE TABLE IF NOT EXISTS items (
    item_id        TEXT PRIMARY KEY,
    platform       TEXT NOT NULL,
    platform_id    TEXT NOT NULL,
    source_id      TEXT NOT NULL REFERENCES sources(source_id),
    category       TEXT,
    title          TEXT,
    url            TEXT,
    published_at   TEXT,
    report_date    TEXT,
    duration_seconds INTEGER DEFAULT 0,
    language       TEXT,
    discovered_at  TEXT DEFAULT (datetime('now')),
    metadata_refreshed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_items_source ON items(source_id);
CREATE INDEX IF NOT EXISTS idx_items_report_date ON items(report_date);

-- 字幕提取状态
CREATE TABLE IF NOT EXISTS extractions (
    item_id               TEXT PRIMARY KEY REFERENCES items(item_id),
    status                TEXT NOT NULL DEFAULT 'pending',
    method                TEXT,
    language              TEXT,
    attempts              INTEGER DEFAULT 0,
    duration_seconds      INTEGER,
    last_timestamp_seconds REAL,
    coverage_ratio        REAL,
    text_chars            INTEGER,
    sha256                TEXT,
    completed_at          TEXT,
    error_type            TEXT,
    error_message         TEXT,
    updated_at            TEXT DEFAULT (datetime('now'))
);

-- 失败跟踪 (可重试 / 终止)
CREATE TABLE IF NOT EXISTS failures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id         TEXT NOT NULL,
    stage           TEXT NOT NULL,
    error_type      TEXT NOT NULL,
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    max_retries     INTEGER DEFAULT 3,
    next_retry_at   TEXT,
    is_terminal     INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

CREATE INDEX IF NOT EXISTS idx_failures_next_retry ON failures(next_retry_at);

-- 日报视图清单
CREATE TABLE IF NOT EXISTS daily_views (
    report_date   TEXT PRIMARY KEY,
    status        TEXT NOT NULL DEFAULT 'pending',
    item_count    INTEGER DEFAULT 0,
    digest_hash   TEXT,
    feishu_token  TEXT,
    published     INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now'))
);

-- 运行日志
CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    command     TEXT NOT NULL,
    status      TEXT NOT NULL,
    started_at  TEXT DEFAULT (datetime('now')),
    ended_at    TEXT,
    summary     TEXT
);

-- Schema 版本
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_version (version) VALUES (1);
"""


def get_db_path(root_dir: str | Path = None) -> str:
    if root_dir is None:
        root_dir = Path(__file__).resolve().parent.parent.parent
    return str(Path(root_dir) / "backfill" / "state" / "backfill.sqlite")


def get_conn(db_path: str = None):
    if db_path is None:
        db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None) -> tuple[bool, str]:
    """初始化数据库。可重复调用，数据不丢失。"""
    if db_path is None:
        db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    try:
        conn = get_conn(db_path)
        conn.executescript(SCHEMA)
        conn.commit()
        conn.close()
        return True, f"数据库已初始化: {db_path}"
    except Exception as e:
        return False, f"初始化失败: {e}"
