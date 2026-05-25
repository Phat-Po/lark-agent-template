"""Entry point: Feishu/Lark WebSocket bot with tool-calling agent."""

import asyncio
import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from lark_oapi.channel import FeishuChannel
from lark_oapi.channel.config import DedupConfig, SafetyConfig

from src.config import (
    APP_ENV,
    DEBUG_ENDPOINTS_ENABLED,
    LARK_APP_ID,
    LARK_APP_SECRET,
    LOG_LEVEL,
    LLM_MODEL,
    LLM_BASE_URL,
    MESSAGE_DEDUP_SECONDS,
)
from src.db import init_db, complete_message, fail_message
from src.logging_utils import configure_logging
from src import agent
from src.harness import metrics
from src.harness.idempotency import claim_or_skip_message
from src.harness.tracing import start_run, complete_run, fail_run
from src.tools import TOOL_DEFINITIONS
from src.tools import messaging

configure_logging(level=getattr(logging, LOG_LEVEL))
log = logging.getLogger("lark_agent")

app = FastAPI(title="Lark Agent Template")

channel: FeishuChannel | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/debug/metrics")
async def debug_metrics(request: Request):
    if not DEBUG_ENDPOINTS_ENABLED:
        raise HTTPException(status_code=404)
    if request.client.host not in ("127.0.0.1", "::1"):
        raise HTTPException(status_code=403)
    return metrics.snapshot()


async def on_message(msg):
    """Handle incoming Feishu message."""
    trace_id = uuid.uuid4().hex[:12]
    chat_id = msg.chat_id
    user_text = msg.content_text or ""
    message_id = getattr(msg, "message_id", "")

    if not user_text.strip():
        return

    if message_id:
        should_process, cached_reply = claim_or_skip_message(message_id)
        if not should_process:
            if cached_reply and channel:
                metrics.inc("messages_idempotent_hit")
                await channel.send(chat_id, {"text": cached_reply})
            else:
                metrics.inc("messages_idempotent_skip")
            return

    sender_open_id = getattr(msg, "sender_id", "") or ""
    metrics.inc("messages_received")
    log.info(
        "message_received",
        extra={
            "event": "message_received",
            "trace_id": trace_id,
            "chat_id": chat_id,
            "sender_id": sender_open_id,
            "message_id": message_id,
        },
    )

    run_id = start_run(trace_id, chat_id, sender_open_id)

    try:
        reply = await agent.chat(
            user_text,
            chat_id,
            sender_open_id=sender_open_id,
            trace_id=trace_id,
            msg=msg,
        )
        log.info(
            "reply_completed",
            extra={"event": "reply_completed", "trace_id": trace_id, "reply_length": len(reply)},
        )
        metrics.inc("messages_replied")
        complete_run(run_id)
        if message_id:
            complete_message(message_id, reply)
        if channel:
            await channel.send(chat_id, {"text": reply})
    except Exception as exc:
        metrics.inc("messages_failed")
        fail_run(run_id, str(exc))
        if message_id:
            fail_message(message_id, str(exc))
        log.exception("message_failed", extra={"event": "message_failed", "trace_id": trace_id})
        if channel:
            await channel.send(chat_id, {"text": "Sorry, an error occurred. Please try again."})


async def on_error(err):
    log.error("channel_error: %s", err, extra={"event": "channel_error"})


@app.on_event("startup")
async def on_startup():
    global channel
    init_db()
    log.info("startup", extra={"event": "startup", "app_env": APP_ENV, "log_level": LOG_LEVEL})

    channel = FeishuChannel(
        app_id=LARK_APP_ID,
        app_secret=LARK_APP_SECRET,
        name_lookup=lambda ids: {},
        safety=SafetyConfig(dedup=DedupConfig(ttl_seconds=MESSAGE_DEDUP_SECONDS)),
    )
    channel.on("message", on_message)
    channel.on("error", on_error)

    messaging.set_channel(channel)

    num_tools = len(TOOL_DEFINITIONS)
    log.info("=" * 50)
    log.info("Lark Agent Template started")
    log.info("  LLM Model:  %s", LLM_MODEL)
    log.info("  LLM Base:   %s", LLM_BASE_URL)
    log.info("  Tools:      %d loaded", num_tools)
    log.info("  Env:        %s", APP_ENV)
    log.info("=" * 50)

    asyncio.create_task(channel.connect())
    log.info("lark_channel_started", extra={"event": "lark_channel_started"})


@app.on_event("shutdown")
async def on_shutdown():
    log.info("shutdown", extra={"event": "shutdown"})
