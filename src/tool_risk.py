"""Tool risk classification.

WRITE_TOOL_NAMES is populated by the tool registry at startup.
Tools in this set receive idempotency protection and confirmation flows.
"""

from __future__ import annotations


def get_write_tool_names() -> set[str]:
    """Return write/destructive tool names from the registry.

    Lazy import to avoid circular dependency with tools package.
    """
    from src.tools.registry import get_write_tool_names as _get
    return _get()
