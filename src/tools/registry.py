"""Tool registry with automatic harness wrapping.

Usage in a tool file:
    from src.tools.registry import register_tool

    @register_tool(
        name="get_calendar",
        description="Get calendar events for a date range",
        parameters={
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
            },
            "required": [],
        },
        risk_level="read",  # "read" | "write" | "destructive"
    )
    async def get_calendar(args: dict) -> dict:
        return {"ok": True, "data": {...}}
"""

from __future__ import annotations

import importlib
import json
import logging
import os
import pkgutil
import time
from typing import Any, Callable, Awaitable

from src.harness.metrics import inc_tool
from src.harness.result import internal_error, param_error, tool_error, tool_ok
from src.harness.schema import validate_tool_args
from src.harness.tracing import record_tool_invocation

log = logging.getLogger("lark_agent.tools.registry")

# Module-level storage
_registry: dict[str, dict] = {}


def register_tool(
    name: str,
    description: str,
    parameters: dict,
    risk_level: str = "read",
) -> Callable:
    """Decorator to register a tool function.

    Args:
        name: Tool name (must be unique)
        description: Human-readable description for the LLM
        parameters: JSON Schema for tool parameters
        risk_level: "read", "write", or "destructive"
    """
    def decorator(func: Callable[..., Awaitable[dict]]) -> Callable:
        _registry[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "risk_level": risk_level,
            "function": func,
        }
        return func
    return decorator


def get_tool_definitions() -> list[dict]:
    """Return tool definitions in OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": entry["name"],
                "description": entry["description"],
                "parameters": entry["parameters"],
            },
        }
        for entry in _registry.values()
    ]


def get_write_tool_names() -> set[str]:
    """Return set of tool names with risk_level 'write' or 'destructive'."""
    return {
        name for name, entry in _registry.items()
        if entry["risk_level"] in ("write", "destructive")
    }


def get_tool_risk(name: str) -> dict | None:
    """Return risk metadata for a tool, or None if unknown."""
    entry = _registry.get(name)
    if entry is None:
        return None
    return {
        "name": entry["name"],
        "risk_level": entry["risk_level"],
    }


async def execute_tool(
    name: str,
    arguments_json: str,
    trace_id: str = "",
    message_id: str = "",
) -> dict:
    """Execute a tool with full harness wrapping.

    1. Validate args against schema
    2. Record metrics
    3. Record tracing
    4. Call the tool function
    5. Return result envelope
    """
    log.info("tool_call", extra={"event": "tool_call", "trace_id": trace_id, "tool_name": name})
    t0 = time.monotonic()

    def _finish(result: dict) -> dict:
        log.info("tool_result", extra={
            "event": "tool_result", "trace_id": trace_id,
            "tool_name": name, "ok": result.get("ok"),
        })
        inc_tool(name, ok=bool(result.get("ok")))
        duration_ms = (time.monotonic() - t0) * 1000
        error_code = (result.get("error") or {}).get("code", "")
        record_tool_invocation(trace_id, name, arguments_json, bool(result.get("ok")), error_code, duration_ms)
        return result

    if name not in _registry:
        return _finish(tool_error("PARAM_ERROR", f"Unknown tool: {name}"))

    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as e:
        return _finish(param_error(f"Invalid JSON arguments: {e}"))

    tool_defs = get_tool_definitions()
    validation_err = validate_tool_args(name, args, tool_defs)
    if validation_err:
        code, detail = validation_err
        return _finish(tool_error(code, detail))

    entry = _registry[name]
    func = entry["function"]

    try:
        if asyncio.iscoroutinefunction(func):
            result = await func(**args)
        else:
            result = func(**args)
        if not isinstance(result, dict):
            result = tool_ok({"result": result})
        return _finish(result)
    except Exception as e:
        log.exception("tool_failed", extra={"event": "tool_failed", "trace_id": trace_id, "tool_name": name})
        return _finish(internal_error(str(e)))


def discover_tools() -> None:
    """Import all .py files in src/tools/ to trigger @register_tool decorators."""
    package_dir = os.path.dirname(__file__)
    for _, module_name, _ in pkgutil.iter_modules([package_dir]):
        if module_name in ("__init__", "registry"):
            continue
        importlib.import_module(f"src.tools.{module_name}")


# Need asyncio for iscoroutinefunction check in execute_tool
import asyncio
