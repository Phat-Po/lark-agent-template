"""Deterministic pending-action policy for protected writes.

Generic template: no member resolution, no social graph — args pass straight
through. The confirm card is the safety boundary.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass

from src.db import (
    clear_all_pending_actions as _db_clear_all,
    delete_pending_action as _db_delete,
    delete_pending_action_by_action_id as _db_delete_by_id,
    load_pending_action as _db_load,
    save_pending_action as _db_save,
    take_pending_action_by_action_id as _db_take_by_id,
    take_pending_action_db as _db_take,
)

log = logging.getLogger("lark_agent.action_policy")

PENDING_ACTION_TTL_SECONDS = 1800
# Grace window after expiry: expired actions survive this long so a late
# button click can still surface a helpful "request expired" message.
PENDING_ACTION_GRACE_SECONDS = 86400


class PolicyError(ValueError):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class PendingAction:
    tool_name: str
    arguments_json: str
    sender_open_id: str
    chat_id: str
    created_at: float
    expires_at: float
    action_id: str = ""
    request_text: str = ""


def canonicalize_arguments(arguments_json: str) -> str:
    """Stable-serialize tool args so the stored payload replays deterministically.

    Generic template: no member resolution, no arg whitelist — pass through.
    """
    try:
        args = json.loads(arguments_json)
    except (json.JSONDecodeError, TypeError):
        return arguments_json
    return json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def store_pending_action(
    chat_id: str,
    sender_open_id: str,
    tool_name: str,
    arguments_json: str,
    *,
    now: float | None = None,
    request_text: str = "",
) -> PendingAction:
    """Store a pending action. Multiple may coexist per user, each with its own
    action_id, so previously-proposed (not yet confirmed) actions stay valid."""
    current_time = time.time() if now is None else now
    action_id = uuid.uuid4().hex[:12]
    action = PendingAction(
        tool_name=tool_name,
        arguments_json=arguments_json,
        sender_open_id=sender_open_id,
        chat_id=chat_id,
        created_at=current_time,
        expires_at=current_time + PENDING_ACTION_TTL_SECONDS,
        action_id=action_id,
        request_text=request_text,
    )
    _db_save(chat_id, sender_open_id, tool_name, arguments_json,
             action.created_at, action.expires_at, action_id=action_id,
             request_text=request_text)
    # Opportunistic cleanup of long-expired rows (keeps a grace window).
    try:
        sweep_expired_pending_actions(current_time - PENDING_ACTION_GRACE_SECONDS)
    except Exception:
        pass
    log.info(
        "store_pending_action",
        extra={"event": "store_pending_action", "action_id": action_id,
               "chat_id": chat_id[:20]},
    )
    return action


def take_pending_action(
    chat_id: str,
    sender_open_id: str,
    *,
    now: float | None = None,
) -> tuple[PendingAction | None, str]:
    current_time = time.time() if now is None else now
    row = _db_take(chat_id, sender_open_id)
    if row is None:
        return None, "missing"
    action = PendingAction(
        tool_name=row["tool_name"],
        arguments_json=row["arguments_json"],
        sender_open_id=sender_open_id,
        chat_id=chat_id,
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        request_text=row.get("request_text", ""),
    )
    if action.expires_at <= current_time:
        return action, "expired"
    return action, "ready"


def clear_pending_action(chat_id: str, sender_open_id: str) -> None:
    _db_delete(chat_id, sender_open_id)


def clear_all_pending_actions() -> None:
    _db_clear_all()


def get_pending_action_id(chat_id: str, sender_open_id: str) -> str | None:
    """Get the action_id of the current pending action (for building confirm card buttons)."""
    row = _db_load(chat_id, sender_open_id)
    if row and row.get("action_id"):
        return row["action_id"]
    return None


def take_pending_action_by_id(
    action_id: str,
    *,
    now: float | None = None,
) -> tuple[PendingAction | None, str]:
    """Look up and take a pending action by action_id (direct DB lookup)."""
    current_time = time.time() if now is None else now
    log.info(
        "take_by_id_lookup",
        extra={"event": "take_by_id_lookup", "action_id": action_id},
    )
    row = _db_take_by_id(action_id)
    if row is None:
        log.warning("take_by_id_miss", extra={"event": "take_by_id_miss", "action_id": action_id})
        return None, "missing"
    action = PendingAction(
        tool_name=row["tool_name"],
        arguments_json=row["arguments_json"],
        sender_open_id=row["sender_open_id"],
        chat_id=row["chat_id"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        action_id=action_id,
        request_text=row.get("request_text", ""),
    )
    if action.expires_at <= current_time:
        log.info("take_by_id_expired", extra={"event": "take_by_id_expired", "action_id": action_id})
        return action, "expired"
    log.info("take_by_id_success", extra={"event": "take_by_id_success", "action_id": action_id})
    return action, "ready"


def clear_pending_action_by_id(action_id: str) -> None:
    """Clear a pending action by action_id."""
    _db_delete_by_id(action_id)


def sweep_expired_pending_actions(cutoff: float) -> None:
    """Delete pending actions whose expires_at is older than cutoff.

    Called with a grace window so freshly-expired actions still survive long
    enough to show the user a helpful 'request expired' message on click.
    """
    from src.db import sweep_expired_pending_actions as _db_sweep
    _db_sweep(cutoff)
