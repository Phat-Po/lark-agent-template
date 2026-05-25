"""Persistent memory: SQLite-backed user preferences, facts, and conversation summaries."""

import logging
from src.db import get_conn
from src.memory.policy import (
    EXPLICIT_MEMORY_SOURCE,
    may_read_memories,
    validate_explicit_delete,
    validate_explicit_write,
)

log = logging.getLogger("lark_agent.memory")


def get_relevant_memories(sender_open_id: str, query: str = "", limit: int = 10) -> list[str]:
    """Retrieve memories owned by an authenticated sender only."""
    if not may_read_memories(sender_open_id):
        return []
    conn = get_conn()
    rows = conn.execute(
        "SELECT content FROM memories WHERE user_id = ? ORDER BY weight DESC, updated_at DESC LIMIT ?",
        (sender_open_id, limit),
    ).fetchall()
    return [r["content"] for r in rows]


def save_memory(
    sender_open_id: str,
    memory_type: str,
    content: str,
    source: str = EXPLICIT_MEMORY_SOURCE,
    *,
    confirmed_by_user: bool = False,
) -> None:
    """Save only an explicitly requested and confirmed memory."""
    validate_explicit_write(
        sender_open_id,
        memory_type,
        content,
        source,
        confirmed_by_user=confirmed_by_user,
    )
    conn = get_conn()
    conn.execute(
        "INSERT INTO memories (user_id, type, content, source) VALUES (?, ?, ?, ?)",
        (sender_open_id, memory_type, content, source),
    )
    conn.commit()
    log.info("persistent_memory_saved: type=%s", memory_type)


def list_memories(sender_open_id: str) -> list[dict]:
    """List memories owned by an authenticated sender only."""
    if not may_read_memories(sender_open_id):
        return []
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, type, content, weight, created_at FROM memories WHERE user_id = ? ORDER BY updated_at DESC",
        (sender_open_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_memory(
    memory_id: int,
    sender_open_id: str,
    *,
    confirmed_by_user: bool = False,
) -> bool:
    """Delete a confirmed memory only when it belongs to the sender."""
    validate_explicit_delete(sender_open_id, confirmed_by_user=confirmed_by_user)
    conn = get_conn()
    cursor = conn.execute(
        "DELETE FROM memories WHERE id = ? AND user_id = ?",
        (memory_id, sender_open_id),
    )
    conn.commit()
    return cursor.rowcount == 1
