# Project Agents — Your Lark Agent

> **Customize this file** for your own deployment. This is a template — replace the
> sections below with your team's specifics.

## Scope

A Feishu/Lark AI agent with tool calling, interactive cards, and observability.
Clone, configure, and run in 5 minutes.

## GitHub

- **Upstream**: https://github.com/Phat-Po/lark-agent-template
- **Your fork**: _<fill in your fork URL>_
- **Branch**: main

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11+ |
| Web Framework | FastAPI |
| Lark SDK | lark-oapi (Python, WebSocket) |
| AI Model | OpenAI-compatible API (OpenAI, DeepSeek, Mimo, Ollama, etc.) |
| Database | SQLite |
| Container | Docker + docker-compose |

## Customization Checklist

When deploying for your team, update these:

- [ ] **`.env`** — Fill in your Feishu app credentials and LLM API key
- [ ] **`BOT_DISPLAY_NAME`** — Set your bot's display name in card headers
- [ ] **System prompt** — Edit `_DEFAULT_SYSTEM_PROMPT` in `src/agent.py` or set `SYSTEM_PROMPT_FILE` in `.env`
- [ ] **Custom tools** — Add your team's tools in `src/tools/` (see `docs/adding-tools.zh.md`)
- [ ] **Timezone** — Change `_LOCAL_TZ` in `src/tools/tasks.py` if not `Asia/Shanghai`
- [ ] **Fork URL** — Update `git clone` commands in docs to point to your fork

## Adding Custom Tools

See [docs/adding-tools.zh.md](docs/adding-tools.zh.md) (中文) or [docs/adding-tools.md](docs/adding-tools.md) (English).

## Built-in Tools

15 tools included: calendar (CRUD), tasks (CRUD), documents (search/read/create/delete/move), messaging, web search.

Tools with `risk_level="write"` or `"destructive"` automatically get button confirmation.

## Runtime Notes

- Python 3.11+ required. macOS default `python3` is often 3.8 — use Docker.
- `.env` is not auto-loaded. Without Docker: `set -a && source .env && set +a` before uvicorn.
- Feishu app setup requires 6 steps — see `docs/feishu-app-setup.zh.md`.

## Deployment

- **Local**: `docker compose up --build`
- **VPS**: See `docs/deploy-vps.zh.md`
- **Development**: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`

## Updating

```bash
git pull origin main
docker compose up --build
```
