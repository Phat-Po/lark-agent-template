# Lark Agent Template

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)

<pre>
██       ████    ███████    ██
██      ██   ██     ██      ██
██      ██████      ██      ██
██      ██   ██     ██      ██
██████  ██   ██     ██      ██
</pre>

**A ready-to-use Feishu/Lark AI agent with tool calling, observability harness, and extensible plugin system.**

[中文文档](README.zh.md)

---

## Get Started in 5 Minutes

> **First time?** Paste [this prompt](docs/onboarding-prompt.md) into ChatGPT, Claude, Cursor, or any AI assistant. It will guide you through every step — from creating a Feishu app to a running bot — and skip steps you've already done.

**Three-step overview:**

```bash
# 1. Clone
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env

# 2. Edit .env — fill in LARK_APP_ID, LARK_APP_SECRET, and LLM_API_KEY
#    (the bot will crash-loop without these — see docs/feishu-app-setup.md)

# 3. Run
docker compose up --build
```

> **Step 2 is required.** The bot will not start without valid credentials in `.env`. If you see `FeishuChannel requires app_id and app_secret` in the logs, you skipped this step.

Look for this in the logs — your bot is live:

```
Lark Agent Template started
  Tools: 15 loaded
connected to wss://msg-frontier.feishu.cn/ws/v2 ...
```

Search for your app name in Feishu and send it a message.

---

## Why Lark Agent Template?

![Before vs After](./marketing/screenshots/02-pain.png)

| Feature | Lark Agent Template | Feishu-OpenAI | nonebot2 |
|---------|:-------------------:|:-------------:|:--------:|
| Language | Python | Go | Python |
| Tool calling with auto-harness | yes | no | no |
| Observability (metrics, tracing) | built-in | no | no |
| Provider-agnostic LLM | yes | OpenAI only | via plugins |
| Template (clone & go) | yes | no | no |
| Conversation memory | session + persistent | yes | via plugins |
| Docker deployment | yes | yes | yes |

---

## Features

![Core capabilities](./marketing/screenshots/03-features.png)

- **Agent loop** — LLM decides when to call tools, results feed back for multi-step reasoning
- **Observability harness** — metrics, tracing, idempotency, schema validation — auto-wraps every tool
- **Extensible** — add custom tools with `@register_tool`, harness coverage is automatic
- **Memory** — session history + per-user persistent long-term memory
- **Provider-agnostic** — any OpenAI-compatible API (OpenAI, DeepSeek, Mimo, Ollama, etc.)
- **15 built-in tools** — calendar, tasks, docs, drive, messaging, web search
- **Write confirmation** — destructive tools require user approval before executing

---

## Built-in Tools

| Tool | Description | Risk |
|------|-------------|:----:|
| `get_calendar` | Read calendar events for a date range | read |
| `create_calendar_event` | Create events with attendees | write |
| `delete_calendar_event` | Delete a calendar event | destructive |
| `get_tasks` | List tasks (filter by status/keyword) | read |
| `get_task` | Get a single task by GUID | read |
| `create_task` | Create a task with due date and assignees | write |
| `delete_task` | Delete a task | destructive |
| `search_docs` | Search Feishu documents by keyword | read |
| `read_doc` | Read full document content | read |
| `create_doc` | Create a new document | write |
| `delete_doc` | Delete a document | destructive |
| `move_file` | Move a file to another folder | write |
| `create_folder` | Create a folder in Drive | write |
| `send_message` | Send a message to user or group | write |
| `search_web` | Search the web via SerpAPI | read |

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in:

| Variable | Default | Description |
|----------|---------|-------------|
| `LARK_APP_ID` | — | Feishu app ID (required) |
| `LARK_APP_SECRET` | — | Feishu app secret (required) |
| `LLM_API_KEY` | — | LLM provider API key (required) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `LLM_MODEL` | `gpt-4o` | Model name |
| `MAX_HISTORY_ROUNDS` | `20` | Max conversation turns in context |
| `MAX_TOKEN_BUDGET` | `3000` | Max tokens in LLM response |
| `REQUIRE_WRITE_CONFIRMATION` | `true` | Ask user before write/destructive tools |
| `SEARCH_API_KEY` | — | SerpAPI key (optional, for web search) |
| `DB_PATH` | `data/agent.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging level |

Switch LLM provider by changing `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. No code changes needed.

---

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
    return tool_ok({"city": city, "temp": "25°C"})
```

Place the file in `src/tools/` and restart — it auto-registers with full harness coverage.

---

## Documentation

### Getting Started

| Doc | What it covers |
|-----|----------------|
| [`docs/onboarding-prompt.md`](docs/onboarding-prompt.md) | **Paste into any AI** for step-by-step guided setup. Asks where you are, skips completed steps. |
| [`docs/feishu-app-setup.md`](docs/feishu-app-setup.md) | Feishu app creation, full permission scopes (60+), event subscription, publish & enable checklist. |

### How It Works

| Doc | What it covers |
|-----|----------------|
| [`docs/architecture.md`](docs/architecture.md) | Message flow, agent loop, harness layer, memory system, tool registry. |
| [`docs/adding-tools.md`](docs/adding-tools.md) | Build custom tools with `@register_tool`. Harness auto-wraps schema, metrics, tracing. |

### Deployment

| Doc | What it covers |
|-----|----------------|
| [`docs/deploy-local-docker.md`](docs/deploy-local-docker.md) | Run on your laptop with Docker Compose. |
| [`docs/deploy-vps.md`](docs/deploy-vps.md) | Deploy to a Linux VPS for 24/7 availability. Systemd service, firewall notes. |

### Quick Reference

| File | What it is |
|------|------------|
| [`.env.example`](.env.example) | All environment variables with comments. Copy to `.env`. |
| [`AGENTS.md`](AGENTS.md) | Project governance, tech stack, constraints. |
| [`tasks/STATUS.md`](tasks/STATUS.md) | Current project state, known issues, validated checklist. |

---

## Architecture

![Message flow](./marketing/screenshots/05-how.png)

```
Feishu ──WebSocket──► Lark Client ──► Agent Loop ◄──► LLM API
                                          │
                                   Tool Registry
                                   (harness wrap)
                                          │
                                    Memory (SQLite)
```

See [docs/architecture.md](docs/architecture.md) for the full design.

---

<details>
<summary>Advanced: VPS Deployment</summary>

Deploy to a Linux VPS for 24/7 availability:

```bash
ssh user@your-vps
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env && nano .env
docker compose up -d --build
```

The agent connects outbound via WebSocket — no inbound ports needed.

See [docs/deploy-vps.md](docs/deploy-vps.md) for systemd service setup and firewall notes.
</details>

<details>
<summary>Development</summary>

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pytest
```

Run tests:
```bash
pytest tests/
```
</details>

---

## License

MIT 2026 [Phat-Po](https://github.com/Phat-Po)

---

<div align="center">
  <sub>Built with <a href="https://github.com/larksuite/oapi-sdk-python">lark-oapi</a> · Star this repo if it helped you!</sub>
</div>
