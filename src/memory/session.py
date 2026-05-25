"""Session memory: in-memory conversation history per chat_id."""

import threading

_lock = threading.Lock()
_store: dict[str, list[dict]] = {}


def _approx_tokens(content: str) -> int:
    """Use one character per token as a conservative multilingual estimate."""
    return max(1, len(content or "")) + 4


def get_session_history(chat_id: str, max_rounds: int = 20,
                        max_tokens: int = 1800) -> list[dict]:
    with _lock:
        messages = _store.get(chat_id, [])
        text_messages = [
            msg for msg in messages
            if msg.get("role") in {"user", "assistant"}
            and "tool_calls" not in msg
            and "tool_call_id" not in msg
        ]
        candidates = text_messages[-max_rounds * 2:]
        retained: list[dict] = []
        used = 0
        for message in reversed(candidates):
            content = message.get("content", "")
            size = _approx_tokens(content)
            if retained and used + size > max_tokens:
                break
            if not retained and size > max_tokens:
                keep_chars = max(0, max_tokens - 4)
                retained.append({**message, "content": content[-keep_chars:] if keep_chars else ""})
                break
            retained.append(dict(message))
            used += size
        return list(reversed(retained))


def append_session_message(chat_id: str, role: str, content: str):
    with _lock:
        if chat_id not in _store:
            _store[chat_id] = []
        _store[chat_id].append({"role": role, "content": content})


def clear_session(chat_id: str):
    with _lock:
        _store.pop(chat_id, None)
