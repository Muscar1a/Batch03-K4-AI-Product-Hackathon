"""SQLite schema migrations and connection helpers."""

import sqlite3
from pathlib import Path
import aiosqlite

SCHEMA_V1 = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_messages (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_name TEXT,
    author_id TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_roles_json TEXT NOT NULL DEFAULT '[]',
    is_staff INTEGER NOT NULL DEFAULT 0,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    reference_message_id TEXT,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bot_messages (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    query_text TEXT NOT NULL,
    response_text TEXT NOT NULL,
    intent TEXT,
    confidence REAL,
    citations_json TEXT NOT NULL DEFAULT '[]',
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_runs (
    run_id TEXT PRIMARY KEY,
    run_type TEXT NOT NULL, -- 'incremental' or 'full'
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL, -- 'running', 'success', 'failed'
    file_count INTEGER DEFAULT 0,
    message_count INTEGER DEFAULT 0,
    checksum TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS source_threads (
    thread_id TEXT PRIMARY KEY,
    parent_forum_id TEXT NOT NULL,
    name TEXT,
    first_seen TEXT NOT NULL,
    last_exported TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    discovery_method TEXT NOT NULL DEFAULT 'probe'
);

CREATE TABLE IF NOT EXISTS sync_cursors (
    key TEXT PRIMARY KEY,
    last_timestamp TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    thread_id TEXT,
    source_message_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    topic TEXT,
    status TEXT NOT NULL DEFAULT 'OPEN', -- 'OPEN', 'BOT_ANSWERED', 'STAFF_ANSWERED', 'ESCALATED'
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS question_answers (
    id TEXT PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    answer_message_id TEXT,
    resolution_source TEXT NOT NULL, -- 'BOT', 'STAFF'
    authority_level TEXT NOT NULL, -- 'STAFF', 'COMMUNITY', 'BOT'
    confidence REAL NOT NULL DEFAULT 1.0,
    staff_confirmed INTEGER NOT NULL DEFAULT 0,
    content_excerpt TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'STAFF_DISCORD', 'OFFICIAL_DOCUMENT', 'TECHNICAL_WEB'
    source_id TEXT NOT NULL,
    authority_role TEXT NOT NULL,
    is_valid INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_facts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    fact_type TEXT NOT NULL,
    fact_value TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    action_type TEXT NOT NULL, -- 'ASK', 'ANSWER', 'FEEDBACK', 'ESCALATE'
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FTS5 Virtual Tables
CREATE VIRTUAL TABLE IF NOT EXISTS fts_source_messages USING fts5(
    id UNINDEXED,
    content,
    author_name,
    channel_name
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_claims USING fts5(
    id UNINDEXED,
    title,
    content
);

-- FTS Sync Triggers
CREATE TRIGGER IF NOT EXISTS source_messages_ai AFTER INSERT ON source_messages BEGIN
    INSERT INTO fts_source_messages(id, content, author_name, channel_name)
    VALUES (new.id, new.content, new.author_name, new.channel_name);
END;

CREATE TRIGGER IF NOT EXISTS source_messages_ad AFTER DELETE ON source_messages BEGIN
    DELETE FROM fts_source_messages WHERE id = old.id;
END;

CREATE TRIGGER IF NOT EXISTS source_messages_au AFTER UPDATE ON source_messages BEGIN
    UPDATE fts_source_messages SET
        content = new.content,
        author_name = new.author_name,
        channel_name = new.channel_name
    WHERE id = old.id;
END;
"""



def init_db_sync(db_path: Path) -> None:
    """Initialize database synchronously for setup or CLI."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_V1)
        conn.commit()


async def init_db_async(db_path: Path) -> None:
    """Initialize database asynchronously."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(SCHEMA_V1)
        await db.commit()
