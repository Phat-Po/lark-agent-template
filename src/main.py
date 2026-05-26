"""Entry point: Feishu/Lark WebSocket bot with tool-calling agent."""

import asyncio
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

configure_logging(level=getattr(logging, LOG_LEVEL))
log = logging.getLogger("lark_agent")

app = FastAPI(title="Lark Agent Template")

channel: FeishuChannel | None = None
_setup_mode = False


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
