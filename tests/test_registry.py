"""Smoke tests for the tool registry."""

import asyncio
import pytest

from src.harness.result import tool_ok


def test_register_and_discover_tools():
    from src.tools import TOOL_DEFINITIONS
    assert len(TOOL_DEFINITIONS) > 0


def test_tool_definitions_format():
    from src.tools import TOOL_DEFINITIONS
    for defn in TOOL_DEFINITIONS:
        assert defn["type"] == "function"
        fn = defn["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn


def test_get_tool_definitions_returns_list():
    from src.tools.registry import get_tool_definitions
    defs = get_tool_definitions()
    assert isinstance(defs, list)
    assert len(defs) > 0


def test_get_write_tool_names_subset():
    from src.tools.registry import get_write_tool_names, get_tool_definitions
    write_names = get_write_tool_names()
    all_names = {d["function"]["name"] for d in get_tool_definitions()}
    assert write_names.issubset(all_names)
    assert len(write_names) > 0


def test_get_write_tool_names_excludes_read():
    from src.tools.registry import get_write_tool_names
    write_names = get_write_tool_names()
    assert "get_calendar" not in write_names
    assert "search_docs" not in write_names
    assert "search_web" not in write_names


def test_register_custom_tool():
    from src.tools.registry import register_tool, get_tool_definitions, _registry

    @register_tool(
        name="_test_custom_tool_xyz",
        description="Test tool",
        parameters={"type": "object", "properties": {}, "required": []},
        risk_level="read",
    )
    async def _my_test_tool() -> dict:
        return tool_ok({"test": True})

    assert "_test_custom_tool_xyz" in _registry
    names = [d["function"]["name"] for d in get_tool_definitions()]
    assert "_test_custom_tool_xyz" in names

    del _registry["_test_custom_tool_xyz"]


def test_execute_tool_dispatches():
    from src.tools.registry import register_tool, execute_tool, _registry

    @register_tool(
        name="_test_dispatch_tool",
        description="Dispatch test",
        parameters={
            "type": "object",
            "properties": {
                "value": {"type": "string"},
            },
            "required": ["value"],
        },
        risk_level="read",
    )
    async def _dispatch_test(value: str) -> dict:
        return tool_ok({"echoed": value})

    result = asyncio.run(execute_tool("_test_dispatch_tool", '{"value": "hello"}'))
    assert result["ok"] is True
    assert result["data"]["echoed"] == "hello"

    del _registry["_test_dispatch_tool"]


def test_execute_tool_unknown_returns_error():
    from src.tools.registry import execute_tool
    result = asyncio.run(execute_tool("__nonexistent_tool__", "{}"))
    assert result["ok"] is False


def test_execute_tool_invalid_json():
    from src.tools.registry import execute_tool
    result = asyncio.run(execute_tool("get_calendar", "not-json"))
    assert result["ok"] is False
    assert result["error"]["code"] in ("PARAM_ERROR",)
