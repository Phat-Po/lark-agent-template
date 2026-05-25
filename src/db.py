import sqlite3
import os
import logging
from pathlib import Path

from src.config import DB_PATH

_conn: sqlite3.Connection | None = None
log = logging.getLogger("lark_agent.db")


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        db_dir = os.path.dirname(DB_PATH)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tool_calls TEXT,
            tool_call_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_conv_chat ON conversations(chat_id, created_at);

        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            weight REAL DEFAULT 1.0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_mem_user ON memories(user_id, type);

        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            payload TEXT,
            result TEXT,
            scheduled_at DATETIME,
            executed_at DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_task_type ON scheduled_tasks(task_type, scheduled_at);

        CREATE TABLE IF NOT EXISTS user_prefs (
            user_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, key)
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            sender_hash TEXT,
            status TEXT DEFAULT 'running',
            error_detail TEXT,
            error_category TEXT DEFAULT '',
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            finished_at DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_run_trace ON agent_runs(trace_id);

        CREATE TABLE IF NOT EXISTS tool_invocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            args_hash TEXT,
            ok INTEGER,
            error_code TEXT,
            duration_ms REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_tool_trace ON tool_invocations(trace_id);

        CREATE TABLE IF NOT EXISTS pending_actions (
            chat_id TEXT NOT NULL,
            sender_open_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            PRIMARY KEY (chat_id, sender_open_id)
        );

        CREATE TABLE IF NOT EXISTS processed_messages (
            message_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'processing',
            reply_text TEXT,
            error_detail TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS idempotency_keys (
            idempotency_key TEXT PRIMARY KEY,
            message_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'success',
            result_summary TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_idem_msg ON idempotency_keys(message_id);

        CREATE TABLE IF NOT EXISTS llm_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trace_id TEXT,
            model TEXT,
            latency_ms REAL,
            finish_reason TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_llm_trace ON llm_calls(trace_id);
    """)
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN sender_open_id TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()


# --- Pending actions CRUD ---

def save_pending_action(
    chat_id: str,
    sender_open_id: str,
    tool_name: str,
    arguments_json: str,
    created_at: float,
    expires_at: float,
    *,
    allow_overwrite: bool = False,
) -> None:
    conn = get_conn()
    if allow_overwrite:
        conn.execute(
            """
            INSERT INTO pending_actions (chat_id, sender_open_id, tool_name, arguments_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(chat_id, sender_open_id) DO UPDATE SET
                tool_name = excluded.tool_name,
                arguments_json = excluded.arguments_json,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (chat_id, sender_open_id, tool_name, arguments_json, created_at, expires_at),
        )
    else:
        conn.execute(
            """
            INSERT INTO pending_actions (chat_id, sender_open_id, tool_name, arguments_json, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chat_id, sender_open_id, tool_name, arguments_json, created_at, expires_at),
        )
    conn.commit()


def load_pending_action(chat_id: str, sender_open_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT tool_name, arguments_json, created_at, expires_at "
        "FROM pending_actions WHERE chat_id = ? AND sender_open_id = ?",
        (chat_id, sender_open_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "tool_name": row["tool_name"],
        "arguments_json": row["arguments_json"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
    }


def take_pending_action_db(chat_id: str, sender_open_id: str) -> dict | None:
    """Atomically delete and return the pending action, or None if absent."""
    conn = get_conn()
    row = conn.execute(
        "SELECT tool_name, arguments_json, created_at, expires_at "
        "FROM pending_actions WHERE chat_id = ? AND sender_open_id = ?",
        (chat_id, sender_open_id),
    ).fetchone()
    if row is None:
        return None
    conn.execute(
        "DELETE FROM pending_actions WHERE chat_id = ? AND sender_open_id = ?",
        (chat_id, sender_open_id),
    )
    conn.commit()
    return {
        "tool_name": row["tool_name"],
        "arguments_json": row["arguments_json"],
        "created_at": row["created_at"],
        "expires_at": row["expires_at"],
    }


def delete_pending_action(chat_id: str, sender_open_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "DELETE FROM pending_actions WHERE chat_id = ? AND sender_open_id = ?",
        (chat_id, sender_open_id),
    )
    conn.commit()


def clear_all_pending_actions() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM pending_actions")
    conn.commit()


# --- Processed messages CRUD ---

def claim_message(message_id: str) -> bool:
    """Attempt to claim a message for processing. Returns True if claimed, False if already exists."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO processed_messages (message_id, status) VALUES (?, 'processing')",
            (message_id,),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def get_message_status(message_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT status, reply_text, error_detail FROM processed_messages WHERE message_id = ?",
        (message_id,),
    ).fetchone()
    if row is None:
        return None
    return {"status": row["status"], "reply_text": row["reply_text"], "error_detail": row["error_detail"]}


def complete_message(message_id: str, reply_text: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE processed_messages SET status = 'completed', reply_text = ?, updated_at = CURRENT_TIMESTAMP WHERE message_id = ?",
        (reply_text, message_id),
    )
    conn.commit()


def fail_message(message_id: str, error_detail: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE processed_messages SET status = 'failed', error_detail = ?, updated_at = CURRENT_TIMESTAMP WHERE message_id = ?",
        (error_detail, message_id),
    )
    conn.commit()


def delete_message_record(message_id: str) -> None:
    conn = get_conn()
    conn.execute("DELETE FROM processed_messages WHERE message_id = ?", (message_id,))
    conn.execute("DELETE FROM idempotency_keys WHERE message_id = ?", (message_id,))
    conn.commit()


def clear_all_processed_messages() -> None:
    conn = get_conn()
    conn.execute("DELETE FROM processed_messages")
    conn.execute("DELETE FROM idempotency_keys")
    conn.commit()


# --- Idempotency keys CRUD ---

def check_idempotency_key(key: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT status, result_summary FROM idempotency_keys WHERE idempotency_key = ?",
        (key,),
    ).fetchone()
    if row is None:
        return None
    return {"status": row["status"], "result_summary": row["result_summary"]}


def record_idempotency_key(key: str, message_id: str, tool_name: str,
                           status: str, result_summary: str = "") -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO idempotency_keys (idempotency_key, message_id, tool_name, status, result_summary)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(idempotency_key) DO UPDATE SET
            status = excluded.status,
            result_summary = excluded.result_summary
        """,
        (key, message_id, tool_name, status, result_summary),
    )
    conn.commit()
