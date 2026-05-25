import hashlib
import logging
import time

from src.db import get_conn

log = logging.getLogger("lark_agent.tracing")


def _hash_value(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def start_run(trace_id: str, chat_id: str, sender_open_id: str = "") -> int | None:
    try:
        sender_hash = _hash_value(sender_open_id) if sender_open_id else None
        cur = get_conn().execute(
            "INSERT INTO agent_runs (trace_id, chat_id, sender_hash) VALUES (?, ?, ?)",
            (trace_id, chat_id, sender_hash),
        )
        get_conn().commit()
        return cur.lastrowid
    except Exception:
        log.warning("trace_start_run_failed", exc_info=True)
        return None


def complete_run(run_id: int) -> None:
    if run_id is None:
        return
    try:
        get_conn().execute(
            "UPDATE agent_runs SET status = 'completed', finished_at = CURRENT_TIMESTAMP WHERE id = ?",
            (run_id,),
        )
        get_conn().commit()
    except Exception:
        log.warning("trace_complete_run_failed", exc_info=True)


def fail_run(run_id: int, error_detail: str, error_category: str = "") -> None:
    if run_id is None:
        return
    try:
        get_conn().execute(
            "UPDATE agent_runs SET status = 'failed', error_detail = ?, error_category = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
            (error_detail[:500], error_category, run_id),
        )
        get_conn().commit()
    except Exception:
        log.warning("trace_fail_run_failed", exc_info=True)


def record_llm_call(
    trace_id: str,
    model: str,
    latency_ms: float,
    finish_reason: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> None:
    try:
        get_conn().execute(
            "INSERT INTO llm_calls (trace_id, model, latency_ms, finish_reason, "
            "prompt_tokens, completion_tokens, total_tokens) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trace_id, model, latency_ms, finish_reason,
             prompt_tokens or None, completion_tokens or None, total_tokens or None),
        )
        get_conn().commit()
    except Exception:
        log.warning("trace_llm_call_failed", exc_info=True)


def record_tool_invocation(
    trace_id: str,
    tool_name: str,
    args_json: str,
    ok: bool,
    error_code: str = "",
    duration_ms: float = 0.0,
) -> None:
    try:
        args_hash = _hash_value(args_json) if args_json else None
        get_conn().execute(
            "INSERT INTO tool_invocations (trace_id, tool_name, args_hash, ok, error_code, duration_ms) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (trace_id, tool_name, args_hash, 1 if ok else 0, error_code, duration_ms),
        )
        get_conn().commit()
    except Exception:
        log.warning("trace_tool_invocation_failed", exc_info=True)
