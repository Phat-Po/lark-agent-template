from __future__ import annotations

from typing import Any


def _build_schema_lookup(tool_defs: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for entry in tool_defs:
        fn = entry.get("function", {})
        name = fn.get("name", "")
        if name:
            lookup[name] = fn.get("parameters", {})
    return lookup


def validate_tool_args(
    tool_name: str,
    args: dict[str, Any],
    tool_defs: list[dict],
) -> tuple[str, str] | None:
    """Validate tool arguments against TOOL_DEFINITIONS JSON schema.

    Returns None if valid, or (error_code, detail) on failure.
    """
    lookup = _build_schema_lookup(tool_defs)

    if tool_name not in lookup:
        return ("PARAM_ERROR", f"Unknown tool: {tool_name}")

    schema = lookup[tool_name]
    properties: dict[str, dict] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    # Check required fields
    for field in required:
        if field not in args:
            return ("PARAM_ERROR", f"Missing required parameter: {field}")

    # Check each provided arg
    for key, value in args.items():
        if key not in properties:
            return ("PARAM_ERROR", f"Unexpected parameter: {key}")

        prop = properties[key]
        expected_type = prop.get("type")

        if expected_type and not _type_matches(value, expected_type):
            return (
                "PARAM_ERROR",
                f"Parameter '{key}' expects {expected_type}, got {type(value).__name__}",
            )

        enum_values = prop.get("enum")
        if enum_values and value not in enum_values:
            return (
                "PARAM_ERROR",
                f"Parameter '{key}' must be one of {enum_values}, got '{value}'",
            )

    return None


def _type_matches(value: Any, expected_type: str) -> bool:
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    expected = type_map.get(expected_type)
    if expected is None:
        return True
    return isinstance(value, expected)
