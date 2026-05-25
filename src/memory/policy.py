"""Authorization and consent rules for persistent memory.

Default policy: all senders are authorized. Override may_read_memories()
to add custom access control (e.g., allowlist of user IDs).
"""

ALLOWED_MEMORY_TYPES = frozenset({"preference", "fact"})
EXPLICIT_MEMORY_SOURCE = "user_explicit"
MAX_MEMORY_CONTENT_LENGTH = 500


class MemoryPolicyError(ValueError):
    """Raised when a persistent-memory operation violates policy."""


def may_read_memories(sender_open_id: str) -> bool:
    """Check if a sender is authorized to read memories.

    Default: all senders allowed. Override for access control.
    """
    return bool(sender_open_id)


def validate_explicit_write(
    sender_open_id: str,
    memory_type: str,
    content: str,
    source: str,
    *,
    confirmed_by_user: bool,
) -> None:
    """Require an explicit, confirmed user request before a memory write."""
    _require_authorized_owner(sender_open_id)
    if not confirmed_by_user:
        raise MemoryPolicyError("Persistent-memory writes require explicit user confirmation.")
    if source != EXPLICIT_MEMORY_SOURCE:
        raise MemoryPolicyError("Inferred or unattributed persistent-memory writes are disabled.")
    if memory_type not in ALLOWED_MEMORY_TYPES:
        raise MemoryPolicyError("Memory type is not allowed.")
    if not isinstance(content, str) or not content.strip():
        raise MemoryPolicyError("Memory content must not be empty.")
    if len(content) > MAX_MEMORY_CONTENT_LENGTH:
        raise MemoryPolicyError("Memory content exceeds the allowed length.")


def validate_explicit_delete(sender_open_id: str, *, confirmed_by_user: bool) -> None:
    """Require an authenticated owner and confirmation before a delete."""
    _require_authorized_owner(sender_open_id)
    if not confirmed_by_user:
        raise MemoryPolicyError("Persistent-memory deletion requires explicit user confirmation.")


def _require_authorized_owner(sender_open_id: str) -> None:
    if not may_read_memories(sender_open_id):
        raise MemoryPolicyError("Persistent-memory owner is not an authorized sender.")
