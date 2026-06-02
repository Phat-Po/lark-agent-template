"""Entry point: Feishu/Lark WebSocket bot with tool-calling agent."""

import asyncio
import base64
import json
import logging
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
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
from src.card_builder import build_reply_card, build_error_card
from src.action_policy import take_pending_action_by_id, clear_pending_action_by_id

configure_logging(level=getattr(logging, LOG_LEVEL))
log = logging.getLogger("lark_agent")

app = FastAPI(title="Lark Agent Template")

channel: FeishuChannel | None = None
_setup_mode = False


# --- SDK monkey-patches ---

def _patch_ws_client_loop():
    """Monkey-patch lark_oapi.ws.client.loop with a fresh, non-running event loop.

    The SDK's WSClient.start() uses a module-level ``loop`` variable and calls
    loop.run_until_complete(). Under uvicorn the main loop is already running,
    so this fails.  We create a fresh loop that is NOT running, so
    run_until_complete() works.  The WSClient.start() runs in a thread via
    run_in_executor, so it can block on this separate loop.
    """
    import lark_oapi.ws.client as ws_client_mod
    ws_client_mod.loop = asyncio.new_event_loop()
    log.info("ws_client_loop_patched", extra={"event": "ws_client_loop_patched"})


def _verify_sdk_patches():
    """Verify critical SDK patches are active at startup."""
    from lark_oapi.ws.client import Client
    import lark_oapi.ws.client as ws_mod

    checks = {
        "ws_client_loop_patched": ws_mod.loop is not None and ws_mod.loop != asyncio.get_event_loop(),
        "card_handler_patched": Client._handle_data_frame.__name__ == "_patched_handle_data_frame",
    }
    for name, ok in checks.items():
        if ok:
            log.info("sdk_patch_verified", extra={"event": "sdk_patch_verified", "patch": name})
        else:
            log.error("sdk_patch_MISSING", extra={"event": "sdk_patch_MISSING", "patch": name})


def _patch_ws_client_card_handler():
    """Monkey-patch WSClient to handle MessageType.CARD messages.

    SDK bug: _handle_data_frame silently drops CARD messages (return instead of
    routing to event handler).  This patch replaces _handle_data_frame with a
    version that routes CARD messages through the same event handler as EVENT.
    """
    from lark_oapi.ws.client import Client, _get_by_key
    from lark_oapi.ws.enum import MessageType
    from lark_oapi.ws.model import Response
    from lark_oapi.ws.const import HEADER_MESSAGE_ID, HEADER_TRACE_ID, HEADER_SUM, HEADER_SEQ, HEADER_TYPE, HEADER_BIZ_RT
    from lark_oapi.core.json import JSON
    from lark_oapi.core.const import UTF_8
    import http
    import time

    async def _patched_handle_data_frame(self, frame):
        """Patched version that handles CARD messages instead of dropping them."""
        hs = frame.headers
        msg_id = _get_by_key(hs, HEADER_MESSAGE_ID)
        trace_id = _get_by_key(hs, HEADER_TRACE_ID)
        sum_ = _get_by_key(hs, HEADER_SUM)
        seq = _get_by_key(hs, HEADER_SEQ)
        type_ = _get_by_key(hs, HEADER_TYPE)

        pl = frame.payload
        if int(sum_) > 1:
            pl = self._combine(msg_id, int(sum_), int(seq), pl)
            if pl is None:
                return

        message_type = MessageType(type_)
        log.info(
            "ws_frame_received",
            extra={"event": "ws_frame_received", "message_type": message_type.value,
                   "msg_id": msg_id, "trace_id": trace_id},
        )

        resp = Response(code=http.HTTPStatus.OK)
        try:
            start = int(round(time.time() * 1000))
            if message_type in (MessageType.EVENT, MessageType.CARD):
                result = self._event_handler._do_without_validation(pl)
            else:
                return
            end = int(round(time.time() * 1000))
            header = hs.add()
            header.key = HEADER_BIZ_RT
            header.value = str(end - start)
            if result is not None:
                resp.data = base64.b64encode(JSON.marshal(result).encode(UTF_8))
        except Exception as e:
            log.error("handle data frame failed: type=%s msg_id=%s err=%s",
                      message_type.value, msg_id, e)
            resp = Response(code=http.HTTPStatus.INTERNAL_SERVER_ERROR)

        frame.payload = JSON.marshal(resp).encode(UTF_8)
        await self._write_message(frame.SerializeToString())

    Client._handle_data_frame = _patched_handle_data_frame
    log.info("ws_client_card_handler_patched", extra={"event": "ws_client_card_handler_patched"})


MAX_CARD_SIZE = 28000  # Feishu card limit ~30KB, leave 2KB buffer


def _truncate_card_content(card: dict, max_bytes: int = MAX_CARD_SIZE) -> dict:
    """Truncate card markdown content if the card JSON exceeds the size limit."""
    card_json = json.dumps(card, ensure_ascii=False)
    if len(card_json.encode("utf-8")) <= max_bytes:
        return card
    for elem in card.get("body", {}).get("elements", []):
        if elem.get("tag") == "markdown":
            content = elem.get("content", "")
            max_chars = max_bytes // 3
            elem["content"] = content[:max_chars] + "\n\n...(content truncated)"
            break
    metrics.inc("card_truncated")
    return card


async def _send_card_with_fallback(chat_id: str, card: dict, trace_id: str, fallback_text: str) -> None:
    """Send a card; fall back to plain text on failure."""
    try:
        card = _truncate_card_content(card)
        result = await channel.send(chat_id, {"card": card})
        if not result.success:
            raise Exception(f"Card send failed: {result.error}")
        metrics.inc("cards_sent")
        log.info(
            "card_sent",
            extra={"event": "card_sent", "trace_id": trace_id, "chat_id": chat_id,
                   "card_size_bytes": len(json.dumps(card, ensure_ascii=False))},
        )
    except Exception as card_err:
        log.warning(
            "card_send_fallback",
            extra={"event": "card_send_fallback", "trace_id": trace_id,
                   "chat_id": chat_id, "error": str(card_err)},
        )
        metrics.inc("card_send_fallback")
        try:
            await channel.send(chat_id, {"text": fallback_text})
        except Exception:
            log.exception("text_fallback_also_failed", extra={"event": "text_fallback_also_failed", "trace_id": trace_id})


async def _ensure_user_gets_response(chat_id: str, trace_id: str, error_msg: str = "Sorry, something went wrong. Please try again.") -> None:
    """Last resort: ensure the user always gets some response."""
    try:
        await _send_card_with_fallback(chat_id, build_error_card(error_msg), trace_id, error_msg)
    except Exception:
        log.exception("ensure_response_failed", extra={"event": "ensure_response_failed", "trace_id": trace_id})


def _setup_checklist() -> str:
    """Generate HTML setup checklist showing what's configured and what's missing."""
    checks = [
        ("LARK_APP_ID", bool(LARK_APP_ID), "Feishu app ID", "https://open.feishu.cn/app → Credentials & Basic Info"),
        ("LARK_APP_SECRET", bool(LARK_APP_SECRET), "Feishu app secret", "Same page as App ID"),
        ("LLM_API_KEY", bool(LLM_API_KEY), "LLM API key", "Your LLM provider (OpenAI/DeepSeek/Mimo)"),
    ]

    all_ok = all(ok for _, ok, _, _ in checks)
    rows = ""
    for name, ok, desc, where in checks:
        icon = "yes" if ok else "no"
        status = "SET" if ok else "EMPTY"
        rows += f'<tr><td class="{icon}">{icon.upper()}</td><td><code>{name}</code></td><td>{desc}</td><td>{where}</td></tr>\n'

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lark Agent Template — Setup</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:#0d1117; color:#c9d1d9; padding:2rem; }}
  .container {{ max-width:720px; margin:0 auto; }}
  h1 {{ font-size:1.8rem; margin-bottom:0.5rem; color:#58a6ff; }}
  .subtitle {{ color:#8b949e; margin-bottom:2rem; }}
  .status {{ padding:1rem 1.5rem; border-radius:8px; margin-bottom:1.5rem; font-weight:600; }}
  .status.ok {{ background:#0d2818; border:1px solid #238636; color:#3fb950; }}
  .status.missing {{ background:#2d1117; border:1px solid #da3633; color:#f85149; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:1.5rem; }}
  th {{ text-align:left; padding:0.6rem 1rem; border-bottom:2px solid #30363d; color:#8b949e; font-size:0.85rem; text-transform:uppercase; }}
  td {{ padding:0.6rem 1rem; border-bottom:1px solid #21262d; }}
  td.yes {{ color:#3fb950; font-weight:700; }}
  td.no {{ color:#f85149; font-weight:700; }}
  code {{ background:#161b22; padding:0.15rem 0.4rem; border-radius:4px; font-size:0.9rem; }}
  h2 {{ font-size:1.2rem; margin:1.5rem 0 0.8rem; color:#c9d1d9; }}
  ol {{ padding-left:1.5rem; line-height:2; }}
  ol li {{ color:#c9d1d9; }}
  ol li code {{ color:#58a6ff; }}
  .footer {{ margin-top:2rem; padding-top:1rem; border-top:1px solid #21262d; color:#8b949e; font-size:0.85rem; }}
  a {{ color:#58a6ff; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .cmd {{ background:#161b22; padding:0.8rem 1rem; border-radius:6px; font-family:monospace; font-size:0.85rem; margin:0.5rem 0; overflow-x:auto; color:#c9d1d9; }}
</style>
</head><body>
<div class="container">
  <h1>Lark Agent Template</h1>
  <p class="subtitle">Bot is running in setup mode — credentials not configured yet.</p>

  <div class="status missing">
    Setup incomplete — the bot cannot connect to Feishu until all required credentials are set.
  </div>

  <table>
    <tr><th></th><th>Variable</th><th>What it is</th><th>Where to get it</th></tr>
    {rows}
  </table>

  <h2>How to fix</h2>
  <ol>
    <li>Edit <code>.env</code> in the project root</li>
    <li>Fill in the EMPTY variables above</li>
    <li>Restart: <code>docker compose up --build</code></li>
  </ol>

  <div class="cmd">
    # Quick edit<br>
    nano .env<br><br>
    # Then restart<br>
    docker compose up --build
  </div>

  <h2>Don't have a Feishu app yet?</h2>
  <ol>
    <li>Go to <a href="https://open.feishu.cn/" target="_blank">open.feishu.cn</a> → Create App → Enterprise Custom App</li>
    <li>Copy <strong>App ID</strong> and <strong>App Secret</strong> → paste into <code>.env</code></li>
    <li>Enable <strong>Bot</strong> capability</li>
    <li>Add permissions (see <a href="https://github.com/Phat-Po/lark-agent-template/blob/main/docs/feishu-app-setup.md">full list</a>)</li>
    <li>Event Subscription → WebSocket mode → add <code>im.message.receive_v1</code></li>
    <li>Publish a version → enable in <a href="https://admin.feishu.cn" target="_blank">admin.feishu.cn</a></li>
  </ol>

  <p class="footer">
    Full guide: <a href="https://github.com/Phat-Po/lark-agent-template/blob/main/docs/onboarding-prompt.md">docs/onboarding-prompt.md</a>
    &nbsp;·&nbsp;
    <a href="https://github.com/Phat-Po/lark-agent-template">GitHub</a>
  </p>
</div>
</body></html>"""


@app.get("/health")
async def health():
    return {"status": "setup" if _setup_mode else "ok"}


@app.get("/", response_class=HTMLResponse)
async def root():
    if _setup_mode:
        return _setup_checklist()
    return '<html><head><meta http-equiv="refresh" content="0;url=/health"></head></html>'


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
                await channel.send(chat_id, {"card": build_reply_card(cached_reply)})
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
        # chat() may return str (normal reply) or dict (confirm card)
        if isinstance(reply, dict) and reply.get("type") == "card":
            card_payload = reply["card"]
            reply_text = "(confirm card sent)"
        else:
            card_payload = build_reply_card(reply)
            reply_text = reply
        log.info(
            "reply_completed",
            extra={"event": "reply_completed", "trace_id": trace_id, "reply_length": len(reply_text)},
        )
        metrics.inc("messages_replied")
        complete_run(run_id)
        if message_id:
            complete_message(message_id, reply_text)
        if channel:
            await _send_card_with_fallback(chat_id, card_payload, trace_id, reply_text)
    except Exception as exc:
        metrics.inc("messages_failed")
        fail_run(run_id, str(exc))
        if message_id:
            fail_message(message_id, str(exc))
        log.exception("message_failed", extra={"event": "message_failed", "trace_id": trace_id})
        if channel:
            error_card = build_error_card("Sorry, an error occurred. Please try again.")
            await _send_card_with_fallback(chat_id, error_card, trace_id, "Sorry, an error occurred. Please try again.")


async def on_error(err):
    log.error("channel_error: %s", err, extra={"event": "channel_error"})


async def on_card_action(event):
    """Handle card button click events (confirm / cancel)."""
    trace_id = uuid.uuid4().hex[:12]
    log.info(
        "card_action_raw",
        extra={"event": "card_action_raw", "trace_id": trace_id, "event_repr": repr(event)[:500]},
    )
    action = event.action
    value = action.value or {}
    inner = value.get("value", value)  # Feishu may nest one layer
    action_type = inner.get("type", "")
    action_id = inner.get("action_id", "")
    tool_name = inner.get("tool", "")

    chat_id = getattr(event, "chat_id", "") or ""
    sender_open_id = getattr(getattr(event, "operator", None), "open_id", "") or ""

    log.info(
        "card_action_received",
        extra={
            "event": "card_action_received",
            "trace_id": trace_id,
            "action_type": action_type,
            "action_id": action_id,
            "tool_name": tool_name,
            "chat_id": chat_id,
            "sender_id": sender_open_id,
        },
    )
    metrics.inc("card_actions_received")

    try:
        if action_type == "confirm":
            pending_action, status = take_pending_action_by_id(action_id)
            log.info(
                "card_action_confirm_status",
                extra={
                    "event": "card_action_confirm_status",
                    "trace_id": trace_id,
                    "action_id": action_id,
                    "status": status,
                    "has_pending": pending_action is not None,
                },
            )
            if status == "missing":
                msg = "This action is no longer valid (already confirmed or cancelled). Please try again."
                await _send_card_with_fallback(chat_id, build_error_card(msg), trace_id, msg)
                return
            if status == "expired":
                msg = agent._expired_request_message(pending_action)
                await _send_card_with_fallback(chat_id, build_error_card(msg), trace_id, msg)
                return
            reply = await agent.execute_pending_action(
                pending_action,
                trace_id=trace_id,
            )
            metrics.inc("card_actions_confirmed")
            await _send_card_with_fallback(chat_id, build_reply_card(reply), trace_id, reply)

        elif action_type == "cancel":
            clear_pending_action_by_id(action_id)
            metrics.inc("card_actions_cancelled")
            await _send_card_with_fallback(chat_id, build_reply_card("Action cancelled."), trace_id, "Action cancelled.")

        else:
            log.warning("unknown_card_action_type", extra={"event": "unknown_card_action_type", "action_type": action_type})
            await _ensure_user_gets_response(chat_id, trace_id, "Unknown action type. Please try again.")

    except Exception as exc:
        log.exception("card_action_handler_error", extra={"event": "card_action_handler_error", "trace_id": trace_id})
        metrics.inc("card_actions_failed")
        await _ensure_user_gets_response(chat_id, trace_id, f"Action failed: {str(exc)[:100]}")


@app.on_event("startup")
async def on_startup():
    global channel, _setup_mode
    init_db()
    log.info("startup", extra={"event": "startup", "app_env": APP_ENV, "log_level": LOG_LEVEL})

    if not LARK_APP_ID or not LARK_APP_SECRET:
        _setup_mode = True
        log.warning("=" * 50)
        log.warning("SETUP MODE — missing credentials, bot running as setup guide")
        log.warning("  LARK_APP_ID=%s", "SET" if LARK_APP_ID else "EMPTY")
        log.warning("  LARK_APP_SECRET=%s", "SET" if LARK_APP_SECRET else "EMPTY")
        log.warning("  Open http://localhost:8080 in your browser for setup instructions")
        log.warning("=" * 50)
        return

    channel = FeishuChannel(
        app_id=LARK_APP_ID,
        app_secret=LARK_APP_SECRET,
        name_lookup=lambda ids: {},
        safety=SafetyConfig(dedup=DedupConfig(ttl_seconds=MESSAGE_DEDUP_SECONDS)),
    )
    channel.on("message", on_message)
    channel.on("error", on_error)
    channel.on("cardAction", on_card_action)

    messaging.set_channel(channel)

    num_tools = len(TOOL_DEFINITIONS)
    log.info("=" * 50)
    log.info("Lark Agent Template started")
    log.info("  LLM Model:  %s", LLM_MODEL)
    log.info("  LLM Base:   %s", LLM_BASE_URL)
    log.info("  Tools:      %d loaded", num_tools)
    log.info("  Env:        %s", APP_ENV)
    log.info("=" * 50)

    # Ensure background loop exists, then apply SDK patches
    channel._ensure_bg_loop()
    _patch_ws_client_loop()
    _patch_ws_client_card_handler()
    _verify_sdk_patches()

    asyncio.create_task(channel.connect())
    log.info("lark_channel_started", extra={"event": "lark_channel_started"})


@app.on_event("shutdown")
async def on_shutdown():
    log.info("shutdown", extra={"event": "shutdown"})
