# Changelog

## v1.1.0 — Interactive cards & persistent confirmation

### Features

- **Interactive Feishu cards** — all replies now render as CardKit v2 cards with colored headers and markdown formatting. Falls back to plain text on card send failure.
- **Button-based confirmation** — protected write/destructive tools show a card with 确认/取消 buttons instead of requiring a text "confirm" reply. Pending actions are persisted in SQLite by `action_id` (survives bot restart, multiple pending actions coexist, 30-minute expiry).
- **Timeout + error sanitization** — external API calls (Feishu messaging) are wrapped with a 15-second timeout. Failures return readable, sanitized error messages.

### Fixes

- **lark-oapi SDK: uvicorn loop crash** — monkey-patched `WSClient.start()` to use a fresh event loop that doesn't conflict with uvicorn's running loop.
- **lark-oapi SDK: dropped CARD messages** — monkey-patched `_handle_data_frame` to route `MessageType.CARD` through the event handler instead of silently dropping them.

### Configuration

- Added `BOT_DISPLAY_NAME` environment variable (default: `Lark Agent`) — controls the display name in card headers.

### Planned for v1.2

- Bitable tools (read/write Feishu Bitable bases)
- User OAuth flow
- Scheduled automation

## v1.0.0 — Initial release

- 15 built-in tools (calendar, tasks, docs, drive, messaging, web search)
- Agent loop with tool calling and multi-step reasoning
- Observability harness (metrics, tracing, idempotency, schema validation)
- Session + persistent memory
- Provider-agnostic LLM (OpenAI-compatible)
- Docker deployment
- Interactive setup mode when credentials are missing
