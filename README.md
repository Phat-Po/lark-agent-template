# Lark Agent Template

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![lark-oapi](https://img.shields.io/badge/lark--oapi-1.4+-0088FF.svg)](https://github.com/larksuite/oapi-sdk-python)

<pre>
██       ████    ███████    ██
██      ██   ██     ██      ██
██      ██████      ██      ██
██      ██   ██     ██      ██
██████  ██   ██     ██      ██
</pre>

**A production-ready Feishu/Lark AI agent with tool calling, interactive cards, and observability — clone, configure, run in 5 minutes.**

📖 [查看简体中文文档](README.zh.md)

---

## Why Lark Agent Template?

Building a Feishu bot that actually *does things* — managing calendars, creating tasks, searching docs — usually means hundreds of lines of boilerplate: API integration, error handling, conversation memory, metrics, idempotency checks. This template gives you all of that out of the box.

| | Lark Agent Template | Feishu-OpenAI | nonebot2-feishu |
|---|:---:|:---:|:---:|
| **Language** | Python 3.11+ | Go | Python |
| **Agent loop with tool calling** | ✅ built-in | ❌ | ❌ |
| **Auto-harness (metrics, tracing, idempotency)** | ✅ every tool | ❌ | ❌ |
| **Interactive cards (CardKit v2)** | ✅ with button confirm | ✅ rich cards | ❌ |
| **Provider-agnostic LLM** | ✅ any OpenAI-compatible | ❌ OpenAI only | via plugins |
| **DB-persisted confirmation** | ✅ survives restart | ❌ | ❌ |
| **Observability dashboard** | ✅ built-in | ❌ | ❌ |
| **Clone & go** | ✅ 5 min setup | ❌ config-heavy | ❌ framework learning curve |
| **License** | MIT | GPL-3.0 | MIT |

---

## ✨ Features

- 🤖 **Agent loop** — LLM decides when to call tools, results feed back for multi-step reasoning
- 🎴 **Interactive cards** — replies render as CardKit v2 cards with colored headers and markdown
- ✅ **Button confirmation** — protected writes show 确认/取消 buttons; persisted in SQLite, survives restart
- 🔧 **15 built-in tools** — calendar, tasks, docs, drive, messaging, web search
- 📊 **Observability harness** — metrics, tracing, idempotency, schema validation — auto-wraps every tool
- 🧠 **Memory** — session history + per-user persistent long-term memory
- 🔌 **Provider-agnostic** — any OpenAI-compatible API (OpenAI, DeepSeek, Mimo, Ollama, etc.)
- 🛡️ **Timeout + error handling** — 15s timeout on API calls, sanitized error messages, text fallback on card failure
- 🐳 **Docker-ready** — one command to build and run

---

## 📦 Installation

```bash
# 1. Clone
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env

# 2. Run (interactive credential prompt if missing)
docker compose run --rm agent
```

The entrypoint checks your credentials. If missing, it prompts you to paste them:

```
============================================================
  Lark Agent Template — Credential Check
============================================================

  LARK_APP_ID is not set.
  Get from: https://open.feishu.cn/app → Credentials & Basic Info

  Enter LARK_APP_ID: cli_xxxxxxxxxxxxxxxx
  Saved to .env
```

After credentials are set, the bot starts. Search for your app name in Feishu and send it a message.

> **Prefer manual setup?** Fill in `LARK_APP_ID`, `LARK_APP_SECRET`, and `LLM_API_KEY` in `.env`, then `docker compose up --build`.

---

## 🚀 Quick Start

Once running, try these in Feishu:

| Say this | What happens |
|----------|-------------|
| "What's on my calendar today?" | Reads your calendar events |
| "Create a task: submit report by Friday" | Shows a confirm card, then creates the task |
| "Search docs for Q2 revenue" | Searches your Feishu documents |
| "Send a message to the marketing group: meeting at 3pm" | Shows confirm card, then sends |
| "What's the weather in Tokyo?" | Calls the web search tool |

Protected write/destructive operations (create, delete, send) show an interactive card with **确认** and **取消** buttons. The pending action is stored in the database — if the bot restarts before you click, the action expires gracefully after 30 minutes.

---

## 🔧 Configuration

All configuration via environment variables. Copy `.env.example` to `.env` and fill in:

| Variable | Default | Description |
|----------|---------|-------------|
| `LARK_APP_ID` | — | Feishu app ID (required) |
| `LARK_APP_SECRET` | — | Feishu app secret (required) |
| `LLM_API_KEY` | — | LLM provider API key (required) |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM API base URL |
| `LLM_MODEL` | `gpt-4o` | Model name |
| `BOT_DISPLAY_NAME` | `Lark Agent` | Display name in card headers |
| `MAX_HISTORY_ROUNDS` | `20` | Max conversation turns in context |
| `MAX_HISTORY_TOKENS` | `1800` | Max tokens from conversation history |
| `MAX_TOKEN_BUDGET` | `3000` | Max tokens in LLM response |
| `REQUIRE_WRITE_CONFIRMATION` | `true` | Ask user before write/destructive tools |
| `MESSAGE_DEDUP_SECONDS` | `300` | Dedup window for incoming messages |
| `SEARCH_API_KEY` | — | SerpAPI key (optional, for web search) |
| `DB_PATH` | `data/agent.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging level |

Switch LLM provider by changing `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`. No code changes needed.

---

## 🛠️ Adding Custom Tools

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

Place the file in `src/tools/` and restart — it auto-registers with full harness coverage (schema validation, metrics, tracing, idempotency).

Tools with `risk_level="write"` or `"destructive"` automatically get the button-confirmation flow. No per-tool work needed.

---

## 📋 Built-in Tools

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

## 🏗️ Architecture

```
Feishu ──WebSocket──► Lark Client ──► Agent Loop ◄──► LLM API
                                          │
                                   Tool Registry
                                   (harness wrap)
                                          │
                                    Memory (SQLite)
                                          │
                                   Interactive Cards
                                   (CardKit v2)
```

Every tool call flows through the harness:

```
execute_tool(name, args)
    ├── Schema validation
    ├── Metrics (count, success/error rate)
    ├── Tracing (SQLite: tool, duration, result)
    ├── Idempotency check (write tools)
    ├── Confirmation guard (write/destructive → button card)
    └── Execute tool function
```

See [docs/architecture.md](docs/architecture.md) for the full design.

---

## 📖 Documentation

| Doc | What it covers |
|-----|----------------|
| [docs/onboarding-prompt.md](docs/onboarding-prompt.md) | **Paste into any AI** for step-by-step guided setup |
| [docs/feishu-app-setup.md](docs/feishu-app-setup.md) | Feishu app creation, permissions, event subscription |
| [docs/architecture.md](docs/architecture.md) | Message flow, agent loop, harness, memory, cards |
| [docs/adding-tools.md](docs/adding-tools.md) | Build custom tools with `@register_tool` |
| [docs/deploy-local-docker.md](docs/deploy-local-docker.md) | Run on your laptop with Docker Compose |
| [docs/deploy-vps.md](docs/deploy-vps.md) | Deploy to a Linux VPS for 24/7 availability |

---

## 🔄 Updating

```bash
bash update.sh
```

Or manually:

```bash
git pull origin main
docker compose up --build
```

---

<details>
<summary>🚀 Advanced: VPS Deployment</summary>

Deploy to a Linux VPS for 24/7 availability:

```bash
ssh user@your-vps
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env && nano .env
docker compose up -d --build
```

The agent connects outbound via WebSocket — no inbound ports needed. The `restart: unless-stopped` policy ensures auto-restart on crash or reboot.

See [docs/deploy-vps.md](docs/deploy-vps.md) for systemd service setup and firewall notes.
</details>

<details>
<summary>🛠️ Development</summary>

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e ".[dev]"
pytest
```

Hot reload during development:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```
</details>

---

## 📄 License

MIT 2026 [Phat-Po](https://github.com/Phat-Po)

---

<div align="center">
  <sub>Built with <a href="https://github.com/larksuite/oapi-sdk-python">lark-oapi</a> · Star this repo if it helped you!</sub>
</div>
