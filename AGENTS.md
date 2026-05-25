# Project AGENTS — lark-agent-template

## Scope

Open-source Feishu/Lark AI bot template. Clone, configure environment variables, and run a working AI agent with tool calling in under 10 minutes.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11 |
| Web Framework | FastAPI |
| Lark SDK | lark-oapi (Python, WebSocket) |
| AI Model | OpenAI-compatible API (Mimo, OpenAI, DeepSeek, etc.) |
| Database | SQLite |
| Scheduler | APScheduler |
| Container | Docker + docker-compose |

## Constraints

- Generic template — no team-specific or org-specific identifiers
- .env not in git, secrets not hardcoded
- SQLite file permissions 600
- Provider-agnostic LLM via OpenAI-compatible SDK
