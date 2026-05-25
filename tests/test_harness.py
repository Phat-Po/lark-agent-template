"""Smoke tests for the observability harness."""

import pytest

from src.harness.result import (
    tool_ok,
    tool_error,
    param_error,
    api_error,
    auth_error,
    internal_error,
)
from src.harness.schema import validate_tool_args


def test_tool_ok_structure():
    result = tool_ok({"key": "value"})
    assert result["ok"] is True
    assert result["data"] == {"key": "value"}


def test_tool_ok_empty():
    result = tool_ok()
    assert result["ok"] is True
    assert result["data"] == {}


def test_tool_error_structure():
    result = tool_error("MY_CODE", "something went wrong")
    assert result["ok"] is False
    assert result["error"]["code"] == "MY_CODE"
    assert result["error"]["detail"] == "something went wrong"


def test_param_error():
    result = param_error("city is required")
    assert result["ok"] is False
    assert result["error"]["code"] == "PARAM_ERROR"
    assert "city" in result["error"]["detail"]


def test_api_error():
    result = api_error("upstream returned 503")
    assert result["ok"] is False
    assert result["error"]["code"] == "API_ERROR"


def test_auth_error():
    result = auth_error("token expired")
    assert result["ok"] is False
    assert result["error"]["code"] == "AUTH_ERROR"


def test_internal_error():
    result = internal_error("unexpected null")
    assert result["ok"] is False
    assert result["error"]["code"] == "INTERNAL_ERROR"


# --- Schema validation ---

_TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "greet",
            "description": "Say hello to someone",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name to greet"},
                    "loud": {"type": "boolean", "description": "Use uppercase"},
                },
                "required": ["name"],
            },
        },
    }
]


def test_validate_passes_valid_args():
    err = validate_tool_args("greet", {"name": "Alice"}, _TOOL_DEFS)
    assert err is None


def test_validate_passes_optional_field():
    err = validate_tool_args("greet", {"name": "Bob", "loud": True}, _TOOL_DEFS)
    assert err is None


def test_validate_catches_missing_required():
    err = validate_tool_args("greet", {}, _TOOL_DEFS)
    assert err is not None
    code, detail = err
    assert "name" in detail.lower() or "required" in detail.lower()


def test_validate_catches_wrong_type():
    err = validate_tool_args("greet", {"name": 42}, _TOOL_DEFS)
    assert err is not None
    code, detail = err
    assert "name" in detail.lower() or "string" in detail.lower()


def test_validate_unknown_tool_returns_error():
    err = validate_tool_args("nonexistent_tool", {"foo": "bar"}, _TOOL_DEFS)
    assert err is not None
    code, detail = err
    assert code == "PARAM_ERROR"
    assert "nonexistent_tool" in detail or "unknown" in detail.lower()
