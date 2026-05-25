"""Structured JSON logging and secret redaction for app and SDK loggers."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

_SENSITIVE_QUERY_RE = re.compile(
    r"(?i)([?&](?:code|access_key|ticket|password|secret|api_key|token)=)([^&#\s\"']+)"
)
_SENSITIVE_JSON_RE = re.compile(
    r'(?i)("(?:code|access_key|ticket|password|secret|api_key|token)"\s*:\s*")([^"]+)(")'
)
_BEARER_RE = re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9\-_.~+/]+=*)")
_OPEN_ID_RE = re.compile(r"\bou_[A-Za-z0-9]{16,32}\b")
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9]{32,}\b")

_EXTRA_FIELDS = (
    "event",
    "trace_id",
    "tool_name",
    "ok",
    "chat_id",
    "sender_id",
    "message_id",
    "reply_length",
)


def redact_secrets(value: Any) -> Any:
    """Redact credentials that may appear in URLs or structured messages."""
    if isinstance(value, str):
        value = _SENSITIVE_QUERY_RE.sub(r"\1[REDACTED]", value)
        value = _SENSITIVE_JSON_RE.sub(r"\1[REDACTED]\3", value)
        value = _BEARER_RE.sub(r"\1[REDACTED]", value)
        value = _OPEN_ID_RE.sub("[REDACTED_ID]", value)
        return value
    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_secrets(item) for item in value]
    return value


def redact_token_like(value: str) -> str:
    """Redact long alphanumeric strings that look like tokens, but preserve
    short identifiers (<=31 chars) to keep logs useful."""
    return _LONG_TOKEN_RE.sub("[REDACTED_TOKEN]", value)


def redact_content(text: str) -> str:
    """Replace message body / user content with a length tag."""
    return f"[content_len={len(text)}]"


def content_hash(text: str) -> str:
    """Return a short hex hash for log correlation without leaking content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", None) or record.getMessage()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": redact_secrets(str(event)),
        }
        message = redact_secrets(record.getMessage())
        if message != payload["event"]:
            payload["message"] = message
        for key in _EXTRA_FIELDS:
            if hasattr(record, key):
                payload[key] = redact_secrets(getattr(record, key))
        if record.exc_info:
            payload["exception"] = redact_secrets(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    """Route application and SDK logs through one redacting JSON formatter."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)

    for name in ("Lark", "lark_oapi", "lark_oapi.ws", "uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
