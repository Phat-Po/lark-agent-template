# Changelog

## v1.1.0 — Interactive cards & persistent confirmation

**Feishu bot replies now render as rich cards with colored headers. Protected operations show confirm/cancel buttons that survive bot restarts.**

### ✨ What's New

- **Interactive Feishu cards (CardKit v2)** — all replies render as cards with colored headers and markdown formatting. Falls back to plain text if card send fails. Configurable display name via `BOT_DISPLAY_NAME`.
- **Button-based confirmation** — write/destructive tools show a card with 确认/取消 buttons instead of requiring a text "confirm" reply. Pending actions are stored in SQLite by `action_id` — survives bot restart, multiple pending actions coexist, 30-minute expiry with graceful handling.
- **lark-oapi SDK bug fixes** — monkey-patched two SDK issues: (1) `WSClient.start()` crash under uvicorn due to event loop conflict, (2) `MessageType.CARD` messages silently dropped instead of routed to event handler.
- **Timeout + error sanitization** — external API calls (Feishu messaging) are wrapped with a 15-second timeout. Failures return readable, sanitized error messages instead of hanging.
- **`.dockerignore`** — prevents `.env`, `data/`, `.git/`, and other sensitive/unnecessary files from being copied into Docker images.

### 🔧 Fixes

- Fixed `docker-compose.yml` restart policy: now `unless-stopped` (matches VPS deployment docs)
- Fixed `docs/deploy-local-docker.md`: hot-reload requires dev override (`docker-compose.dev.yml`), not default
- Removed unused dependencies: `apscheduler`, `pyyaml` from `requirements.txt`
- Removed dead code: `handle_message` alias in `agent.py`
- Added `MESSAGE_DEDUP_SECONDS` to `.env.example` (was in code but undocumented)

### 📦 Installation

```bash
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env
docker compose run --rm agent
```

### 📋 Requirements

- Python 3.11+ (or Docker)
- A Feishu/Lark app with Bot capability ([setup guide](docs/feishu-app-setup.md))
- An OpenAI-compatible LLM API key

### 🔜 Planned for v1.2

- Bitable tools (read/write Feishu Bitable bases)
- User OAuth flow
- Scheduled automation

---

## v1.0.0 — Initial release

- 15 built-in tools (calendar, tasks, docs, drive, messaging, web search)
- Agent loop with tool calling and multi-step reasoning
- Observability harness (metrics, tracing, idempotency, schema validation)
- Session + persistent memory
- Provider-agnostic LLM (OpenAI-compatible)
- Docker deployment with interactive setup mode
