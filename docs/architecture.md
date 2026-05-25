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

## Database schema

```sql
conversations      -- full message log (user + assistant turns)
memories           -- persistent per-user memories
agent_runs         -- one row per message processed (tracing)
llm_calls          -- one row per LLM API call (latency, tokens)
tool_invocations   -- one row per tool call (duration, result)
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
| `SYSTEM_PROMPT_FILE` | — | Path to custom system prompt file |
| `DB_PATH` | data/agent.db | SQLite database path |
| `LOG_LEVEL` | INFO | Logging level |

## Adding a provider

The agent uses the OpenAI-compatible SDK (`openai` Python package). To switch providers, change `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `.env`. No code changes needed.

Tested providers: OpenAI, DeepSeek, Mimo, Ollama (local).
