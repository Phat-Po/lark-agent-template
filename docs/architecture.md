# Architecture

## Message flow

```
Feishu app
    │  WebSocket (long connection)
    ▼
FeishuChannel (lark-oapi)
    │  on_message callback
    ▼
src/main.py — on_message()
    │  Idempotency check (skip duplicates)
    │  Tracing: start_run()
    ▼
src/agent.py — chat()
    │  Load session history
    │  Load persistent memories
    │  Build system prompt
    ▼
_run_agent_loop()
    │  POST to LLM API (OpenAI-compatible)
    │  ◄─── tool_calls in response ───►
    │            │
    │       execute_tool()
    │            │
    │       Tool Registry
    │       (harness-wrapped)
    │            │
    │       Feishu API / external APIs
    │            │
    │       Result → feed back to LLM
    │  ◄─── repeat up to 10 rounds ──►
    │  Final text reply
    ▼
src/main.py — channel.send()
    │
    ▼
Feishu app (user sees reply)
```

## Harness layer

Every tool call flows through the harness before reaching your tool function:

```
execute_tool(name, args_json)
    │
    ├── 1. Schema validation (validate_tool_args)
    │       Check required params, types against JSON Schema
    │
    ├── 2. Metrics (inc_tool)
    │       Count calls, track success/error rate
    │
    ├── 3. Tracing (record_tool_invocation)
    │       Write to SQLite: tool name, duration, result code
    │
    └── 4. Execute tool function
            Return result envelope {ok, data, error}
```

Idempotency for write tools is handled in `src/agent.py` before calling `execute_tool`, so repeated messages don't re-execute the same write.

## Memory system

| Type | Storage | Scope | Purpose |
|------|---------|-------|---------|
| Session | In-memory dict | Per conversation | Conversation history for the LLM context window |
| Persistent | SQLite `memories` table | Per user (sender_open_id) | Long-term facts, preferences, summaries |

Session memory is capped by `MAX_HISTORY_ROUNDS` and `MAX_HISTORY_TOKENS`. Only text messages (not tool call records) are included in the context window.

Persistent memory is retrieved via `get_relevant_memories()` and prepended to the system prompt.

## Interactive cards

Replies are rendered as CardKit v2 cards (colored header + markdown body) instead of plain text. This gives users richer formatting — bold, lists, links — and enables button-based interactions.

### Card types

| Card | Header color | Purpose |
|------|-------------|---------|
| `build_reply_card(text)` | Blue (default) | Normal agent replies |
| `build_confirm_card(text, tool, action_id)` | Blue | Protected write confirmation with 确认/取消 buttons |
| `build_error_card(error_text)` | Red | Error messages |

### SDK monkey-patches

Two patches are applied at startup to work around lark-oapi SDK bugs:

1. **`_patch_ws_client_loop()`** — The SDK's `WSClient.start()` uses a module-level `loop` variable that conflicts with uvicorn's running event loop. This patch creates a fresh, non-running loop so `run_until_complete()` works in the WSClient thread.

2. **`_patch_ws_client_card_handler()`** — The SDK's `_handle_data_frame` silently drops `MessageType.CARD` messages (returns instead of routing to the event handler). This patch replaces it with a version that routes CARD messages through the same event handler as EVENT messages, enabling `channel.on("cardAction", ...)` to work.

### Fallback strategy

Every card send goes through `_send_card_with_fallback()`: if the card send fails (size limit, API error), it falls back to plain text. Cards exceeding 28KB are automatically truncated.

## DB-persisted confirmation flow

When a write/destructive tool is called:

1. The agent stores a `pending_action` row in SQLite (keyed by `action_id`, a UUID).
2. A confirm card with 确认/取消 buttons is returned to the user.
3. On button click, `on_card_action` looks up the `action_id` in the DB and either executes or cancels.
4. Pending actions expire after 30 minutes (`PENDING_ACTION_TTL_SECONDS`). Expired clicks show a helpful message.
5. Multiple pending actions can coexist per user — each has its own `action_id`.

This design survives bot restarts (DB-backed, not in-memory).

## Timeout wrapper

External API calls (e.g. Feishu messaging) are wrapped with `with_timeout()` (15-second default). On timeout, a sanitized error message is returned instead of hanging.

## Database schema

```sql
conversations      -- full message log (user + assistant turns)
memories           -- persistent per-user memories
agent_runs         -- one row per message processed (tracing)
llm_calls          -- one row per LLM API call (latency, tokens)
tool_invocations   -- one row per tool call (duration, result)
pending_actions    -- DB-persisted confirmation buttons (action_id PK, expires_at)
messages           -- idempotency table (message_id → status)
idempotency_keys   -- write-tool dedup (hash → result)
```

## Configuration

All configuration is via environment variables. See `.env.example` for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `LARK_APP_ID` | — | Feishu app ID (required) |
| `LARK_APP_SECRET` | — | Feishu app secret (required) |
| `LLM_API_KEY` | — | LLM provider API key (required) |
| `LLM_BASE_URL` | openai | LLM API base URL |
| `LLM_MODEL` | gpt-4o | Model name |
| `MAX_HISTORY_ROUNDS` | 20 | Max conversation turns to include |
| `MAX_TOKEN_BUDGET` | 3000 | Max tokens in LLM response |
| `REQUIRE_WRITE_CONFIRMATION` | true | Ask user before write/destructive tools |
| `BOT_DISPLAY_NAME` | Lark Agent | Display name shown in card headers |
| `SYSTEM_PROMPT_FILE` | — | Path to custom system prompt file |
| `DB_PATH` | data/agent.db | SQLite database path |
| `LOG_LEVEL` | INFO | Logging level |

## Adding a provider

The agent uses the OpenAI-compatible SDK (`openai` Python package). To switch providers, change `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `.env`. No code changes needed.

Tested providers: OpenAI, DeepSeek, Mimo, Ollama (local).
