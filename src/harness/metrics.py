"""In-process aggregate operational metrics.

All counters are plain integers protected by a single threading.Lock.
No message content, identifiers, or credentials are stored here.
"""

from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone

_lock = threading.Lock()

_counters: dict = {
    "process_start": datetime.now(timezone.utc).isoformat(),
    "messages_received": 0,
    "messages_replied": 0,
    "messages_failed": 0,
    "tool_calls": {},
    "llm_calls": 0,
    "llm_failures": 0,
}


def inc(name: str, amount: int = 1) -> None:
    """Increment a top-level integer counter."""
    with _lock:
        _counters[name] = _counters.get(name, 0) + amount


def inc_tool(tool_name: str, *, ok: bool) -> None:
    """Record a tool outcome by name and success/failure."""
    bucket = "ok" if ok else "error"
    with _lock:
        tool_stats = _counters["tool_calls"].setdefault(tool_name, {"ok": 0, "error": 0})
        tool_stats[bucket] += 1


def snapshot() -> dict:
    """Return a frozen copy of all counters."""
    with _lock:
        return copy.deepcopy(_counters)
