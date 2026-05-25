"""Persistent message-level and write-tool-level idempotency."""

from __future__ import annotations

import hashlib
import json
import logging

from src import db
from src.tool_risk import get_write_tool_names

log = logging.getLogger("lark_agent.idempotency")


def claim_or_skip_message(message_id: str) -> tuple[bool, str | None]:
    """Check message idempotency. Returns (should_process, cached_reply).

    - New message -> claim it, return (True, None)
    - Already completed -> return (False, cached_reply)
    - Currently processing (concurrent dup) -> return (False, None)
    - Previously failed -> re-claim for retry, return (True, None)
    """
    if not message_id:
        return True, None

    existing = db.get_message_status(message_id)
    if existing is None:
        claimed = db.claim_message(message_id)
        if claimed:
            log.info("message_claimed", extra={"event": "message_claimed", "message_id": message_id})
            return True, None
        # Race: another goroutine claimed between check and insert
        log.info("message_race_lost", extra={"event": "message_race_lost", "message_id": message_id})
        return False, None

    status = existing["status"]
    if status == "completed":
        log.info("message_already_processed", extra={"event": "message_already_processed", "message_id": message_id})
        return False, existing.get("reply_text")
    if status == "processing":
        log.info("message_concurrent_skip", extra={"event": "message_concurrent_skip", "message_id": message_id})
        return False, None
    # status == 'failed' -> allow retry
    log.info("message_retry_after_failure", extra={"event": "message_retry_after_failure", "message_id": message_id})
    db.delete_message_record(message_id)
    db.claim_message(message_id)
    return True, None


def make_write_idempotency_key(message_id: str, tool_name: str, args_json: str) -> str:
    """Generate deterministic idempotency key for a write tool call."""
    normalized = _normalize_args_for_key(tool_name, args_json)
    payload = f"{message_id}:{tool_name}:{normalized}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def check_write_idempotency(message_id: str, tool_name: str, args_json: str) -> tuple[bool, dict | None]:
    """Check if a write tool call was already executed. Returns (should_execute, cached_result).

    - No prior record -> (True, None)
    - Prior success -> (False, cached_result)
    - Prior failure -> (True, None) -- allow retry
    """
    if not message_id or tool_name not in get_write_tool_names():
        return True, None

    key = make_write_idempotency_key(message_id, tool_name, args_json)
    existing = db.check_idempotency_key(key)
    if existing is None:
        return True, None
    if existing["status"] == "success":
        log.info(
            "write_idempotent_skip",
            extra={"event": "write_idempotent_skip", "message_id": message_id, "tool_name": tool_name},
        )
        cached = _deserialize_result_summary(existing.get("result_summary"))
        return False, cached
    # failed -> allow retry
    return True, None


def record_write_result(message_id: str, tool_name: str, args_json: str, result: dict) -> None:
    """Record the result of a write tool call for idempotency."""
    if not message_id or tool_name not in get_write_tool_names():
        return

    key = make_write_idempotency_key(message_id, tool_name, args_json)
    status = "success" if result.get("ok") else "failed"
    summary = _serialize_result_summary(result)
    db.record_idempotency_key(key, message_id, tool_name, status, summary)
    log.info(
        "write_result_recorded",
        extra={"event": "write_result_recorded", "message_id": message_id, "tool_name": tool_name, "status": status},
    )


def _normalize_args_for_key(tool_name: str, args_json: str) -> str:
    """Normalize args JSON for deterministic hashing.

    Strips confirmed_by_user (always true on replay) and sorts keys.
    """
    try:
        args = json.loads(args_json)
    except (json.JSONDecodeError, TypeError):
        return args_json or ""
    args.pop("confirmed_by_user", None)
    return json.dumps(args, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _serialize_result_summary(result: dict) -> str:
    """Store a compact result summary (ok status + key data fields)."""
    summary = {"ok": result.get("ok")}
    data = result.get("data")
    if isinstance(data, dict):
        for key in ("task_id", "guid", "event_id", "file_token", "name", "url"):
            if key in data:
                summary[key] = data[key]
    return json.dumps(summary, ensure_ascii=False)


def _deserialize_result_summary(raw: str | None) -> dict:
    if not raw:
        return {"ok": True, "data": {}}
    try:
        summary = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"ok": True, "data": {}}
    return {"ok": summary.get("ok", True), "data": summary}
