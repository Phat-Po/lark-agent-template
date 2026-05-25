# Lark Agent Template

A ready-to-use AI bot template for Feishu/Lark with tool calling,
observability harness, and extensible plugin system.

## Features

- **Tool-calling agent loop** — LLM decides when to call tools,
  results feed back for multi-step reasoning
- **5 built-in tools** — Calendar, Documents, Tasks, Messaging, Web Search
- **Observability harness** — Metrics, tracing, idempotency,
  schema validation — automatically applied to all tools
- **Extensible** — Add custom tools with a single decorator,
  harness wraps them automatically
- **Provider-agnostic LLM** — Works with any OpenAI-compatible API
  (OpenAI, DeepSeek, Mimo, Ollama, etc.)
- **Conversation memory** — Session history + persistent long-term memory
- **Easy deployment** — Docker Compose locally or on any VPS

## Quickstart (5 minutes)

### 1. Clone and configure

```
git clone https://github.com/your-org/lark-agent-template.git
cd lark-agent-template
cp .env.example .env
```

Edit `.env` and fill in your Feishu app credentials and LLM API key.
See [Feishu App Setup](docs/feishu-app-setup.md) for how to create an app.

### 2. Run

```
docker compose up --build
```

### 3. Test

Send a message to your bot in Feishu. You should get a reply within a few seconds.

## Adding Custom Tools

```python
from src.tools.registry import register_tool
from src.harness.result import tool_ok

@register_tool(
    name="get_weather",
    description="Get current weather for a city",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
    },
    risk_level="read",
)
async def get_weather(city: str) -> dict:
    # your implementation here
    return tool_ok({"city": city, "temp": "25°C"})
```

Place the file in `src/tools/` and restart — it auto-registers with full harness coverage.
See [docs/adding-tools.md](docs/adding-tools.md) for the full guide.

## Architecture

```
Feishu ──WebSocket──► Lark Client ──► Agent Loop ◄──► LLM API
                                           │
                                    Tool Registry
                                    (harness-wrapped)
                                           │
                                     Memory (SQLite)
```

## Documentation

- [Feishu App Setup](docs/feishu-app-setup.md) — Create your Feishu app
- [Adding Tools](docs/adding-tools.md) — Build custom tools
- [Local Docker Deployment](docs/deploy-local-docker.md)
- [VPS Deployment](docs/deploy-vps.md)
- [Architecture Details](docs/architecture.md)

## Built-in Tools

| Tool | Description | Risk Level |
|------|-------------|------------|
| `get_calendar` | Read calendar events | read |
| `create_calendar_event` | Create calendar events | write |
| `search_docs` | Search documents | read |
| `create_doc` | Create a document | write |
| `get_tasks` | List tasks | read |
| `create_task` | Create a task | write |
| `send_message` | Send a chat message | write |
| `search_web` | Search the web | read |

## License

MIT
