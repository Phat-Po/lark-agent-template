"""Tool risk classification.

WRITE_TOOL_NAMES is populated by the tool registry at startup.
Tools in this set receive idempotency protection and confirmation flows.
"""

from __future__ import annotations

WRITE_TOOL_NAMES: set[str] = set()
