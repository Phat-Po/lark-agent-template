# Project AGENTS — lark-agent-template

## Scope

Open-source Feishu/Lark AI bot template. Clone, configure environment variables, and run a working AI agent with tool calling in under 10 minutes.

## GitHub

- **Repo**: https://github.com/Phat-Po/lark-agent-template
- **Release**: v1.1.0 (2026-06-02)
- **Branch**: main (only)

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
| CI | GitHub Actions (pytest, Python 3.11/3.12) |

## Constraints

- Generic template — no team-specific or org-specific identifiers
- .env not in git, secrets not hardcoded
- SQLite file permissions 600
- Provider-agnostic LLM via OpenAI-compatible SDK
- Bilingual docs (English + Chinese)

## Built-in Tools

Calendar (read/create/delete), Tasks (CRUD), Documents (search/read/create/delete/move), Messaging, Web Search — 15 tools total with auto-harness wrapping.

## Runtime Notes

- Python 3.11+ required. macOS default `python3` is often 3.8 — use Docker.
- `.env` is not auto-loaded. Without Docker: `set -a && source .env && set +a` before uvicorn.
- Feishu app setup requires 6 steps — see `docs/feishu-app-setup.md` and `tasks/STATUS.md`.

## Release Workflow

```bash
git tag v<version>
git push origin v<version>
gh release create v<version> --repo Phat-Po/lark-agent-template --title "v<version>" --notes "..."
```
