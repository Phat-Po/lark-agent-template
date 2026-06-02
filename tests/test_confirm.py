"""Tests for confirmation flow, card builder, and timeout wrapper."""

import asyncio
import json
import os
import sqlite3
import time

import pytest


# --- Fixtures ---

@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    """Point DB_PATH to a temp file so tests don't touch production data."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    # Force re-import so config picks up the new DB_PATH
    import src.config
    src.config.DB_PATH = db_path
    # Reset the module-level connection so get_conn() creates a fresh one
    import src.db
    src.db._conn = None
    src.db.init_db()
    yield
    src.db._conn = None


# --- Pending-action persistence ---

def test_store_and_take_pending_action():
    from src.action_policy import store_pending_action, take_pending_action_by_id

    action = store_pending_action(
        chat_id="chat1",
        sender_open_id="user1",
        tool_name="create_doc",
        arguments_json='{"title":"test"}',
        request_text="create a doc",
    )
    assert action.action_id
    assert action.tool_name == "create_doc"

    # Take by action_id — should succeed once
    taken, status = take_pending_action_by_id(action.action_id)
    assert taken is not None
    assert status == "ready"
    assert taken.tool_name == "create_doc"

    # Second take — should be missing
    taken2, status2 = take_pending_action_by_id(action.action_id)
    assert taken2 is None
    assert status2 == "missing"


def test_expired_pending_action():
    from src.action_policy import store_pending_action, take_pending_action_by_id, PENDING_ACTION_TTL_SECONDS

    now = time.time()
    action = store_pending_action(
        chat_id="chat1",
        sender_open_id="user1",
        tool_name="create_doc",
        arguments_json='{}',
        now=now - PENDING_ACTION_TTL_SECONDS - 1,  # already expired
    )

    taken, status = take_pending_action_by_id(action.action_id, now=now)
    assert taken is not None
    assert status == "expired"


def test_multiple_pending_actions_coexist():
    from src.action_policy import store_pending_action, take_pending_action_by_id

    a1 = store_pending_action("chat1", "user1", "create_doc", '{"title":"one"}')
    a2 = store_pending_action("chat1", "user1", "create_task", '{"summary":"two"}')

    # Both should be retrievable
    taken1, s1 = take_pending_action_by_id(a1.action_id)
    assert s1 == "ready"
    taken2, s2 = take_pending_action_by_id(a2.action_id)
    assert s2 == "ready"


def test_clear_pending_action_by_id():
    from src.action_policy import store_pending_action, clear_pending_action_by_id, take_pending_action_by_id

    action = store_pending_action("chat1", "user1", "create_doc", '{}')
    clear_pending_action_by_id(action.action_id)

    taken, status = take_pending_action_by_id(action.action_id)
    assert taken is None
    assert status == "missing"


def test_sweep_expired_pending_actions():
    from src.action_policy import store_pending_action, sweep_expired_pending_actions
    from src.db import load_pending_action

    now = time.time()
    # Store an action that expired long ago
    store_pending_action("chat1", "user1", "create_doc", '{}', now=now - 100000)
    # Sweep anything expired more than 86400s ago
    sweep_expired_pending_actions(now - 86400)

    row = load_pending_action("chat1", "user1")
    assert row is None


# --- Timeout wrapper ---

def test_with_timeout_raises_on_slow():
    from src.harness.timeout import with_timeout

    async def _slow():
        await asyncio.sleep(10)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.get_event_loop().run_until_complete(with_timeout(_slow(), timeout=0.01))


def test_with_timeout_succeeds_fast():
    from src.harness.timeout import with_timeout

    async def _fast():
        return 42

    result = asyncio.get_event_loop().run_until_complete(with_timeout(_fast(), timeout=5))
    assert result == 42


# --- Card builder ---

def test_build_reply_card_default_title():
    from src.card_builder import build_reply_card
    from src.config import BOT_DISPLAY_NAME

    card = build_reply_card("Hello world")
    # Card is a dict with body elements
    assert isinstance(card, dict)
    card_json = json.dumps(card, ensure_ascii=False)
    assert BOT_DISPLAY_NAME in card_json
    assert "Hello world" in card_json


def test_build_confirm_card_contains_action_id():
    from src.card_builder import build_confirm_card

    card = build_confirm_card(
        text="Please confirm",
        tool_name="create_doc",
        action_id="abc123",
    )
    card_json = json.dumps(card, ensure_ascii=False)
    assert "abc123" in card_json
    assert "create_doc" in card_json
    assert "confirm" in card_json


def test_build_confirm_card_has_two_buttons():
    from src.card_builder import build_confirm_card

    card = build_confirm_card("t", "create_doc", "abc123")
    card_json = json.dumps(card, ensure_ascii=False)
    # Should have both confirm and cancel button values
    assert '"type": "confirm"' in card_json
    assert '"type": "cancel"' in card_json


def test_build_error_card_is_red():
    from src.card_builder import build_error_card

    card = build_error_card("Something broke")
    card_json = json.dumps(card, ensure_ascii=False)
    assert "red" in card_json
    assert "Something broke" in card_json


# --- Canonicalize arguments ---

def test_canonicalize_arguments_sorts_keys():
    from src.action_policy import canonicalize_arguments

    result = canonicalize_arguments('{"z":1,"a":2}')
    parsed = json.loads(result)
    assert list(parsed.keys()) == ["a", "z"]


def test_canonicalize_arguments_passthrough_invalid():
    from src.action_policy import canonicalize_arguments

    bad = "not json"
    assert canonicalize_arguments(bad) == bad


# --- Sanitize reply ---

def test_sanitize_reply_empty():
    from src.agent import sanitize_reply

    result = sanitize_reply("")
    assert result  # should return fallback, not empty


def test_sanitize_reply_preserves_content():
    from src.agent import sanitize_reply

    result = sanitize_reply("  **bold** text  ")
    assert result == "**bold** text"
