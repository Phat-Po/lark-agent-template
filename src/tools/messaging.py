"""Feishu/Lark messaging tools."""

import asyncio
import logging

from src.logging_utils import content_hash, redact_content
from src.harness.result import api_error, tool_ok
from src.harness.timeout import with_timeout
from src.tools.registry import register_tool

log = logging.getLogger("lark_agent.tools.messaging")

_channel = None


def set_channel(channel):
    """Set the Feishu WebSocket channel for sending messages."""
    global _channel
    _channel = channel


@register_tool(
    name="send_message",
    description="Send a Feishu message to a user or group chat.",
    parameters={
        "type": "object",
        "properties": {
            "receive_id": {"type": "string", "description": "Receiver ID (chat_id or open_id)"},
            "text": {"type": "string", "description": "Message content"},
            "id_type": {"type": "string", "enum": ["chat_id", "open_id"], "description": "ID type, default chat_id"},
        },
        "required": ["receive_id", "text"],
    },
    risk_level="write",
)
async def send_message(receive_id: str, text: str, id_type: str = "chat_id") -> dict:
    log.info("send_message to=%s type=%s %s hash=%s",
             receive_id, id_type, redact_content(text), content_hash(text))

    if _channel is None:
        return api_error("Feishu channel is not initialized.")

    try:
        await with_timeout(_channel.send(receive_id, {"text": text}, {"receive_id_type": id_type}))
        return tool_ok({"success": True})
    except asyncio.TimeoutError:
        log.warning("send_message timeout to=%s", receive_id)
        return api_error("The messaging API timed out. Please try again.")
    except Exception as e:
        log.exception("send_message failed")
        return api_error(str(e))
