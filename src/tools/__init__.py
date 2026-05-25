"""Tools subsystem with auto-discovery and registry."""

from src.tools.registry import discover_tools, get_tool_definitions, execute_tool, get_write_tool_names

# Auto-discover all tool files in this package
discover_tools()

TOOL_DEFINITIONS = get_tool_definitions()
