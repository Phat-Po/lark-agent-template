# Project Status — lark-agent-template

## Current State

**Status**: Stable / Maintain
**Last active**: 2026-05-26
**Release**: v1.0.0 (published on GitHub)

## What works

- Docker startup: `docker compose up --build` → bot live in ~30s
- WebSocket connection to Feishu confirmed stable
- End-to-end message flow verified: 飞书消息 → GPT-4o → 回复
- 15 built-in tools loaded correctly
- Python 3.11 required (3.8 default on macOS breaks `X | None` syntax)

## Known issues / gotchas

- Must run with Python 3.11+. System `python3` on macOS is often 3.8 — use Docker to avoid this.
- `.env` is not auto-loaded by `config.py`. When running without Docker, must `source .env` before uvicorn, or use `set -a && source .env && set +a`.
- Feishu app setup has 6 required steps that are easy to miss — documented in `docs/feishu-app-setup.md`.

## Feishu app setup checklist (validated 2026-05-26)

1. Create Enterprise Custom App → copy App ID + App Secret
2. Add App Capability → **Bot** (required or bot won't appear in search)
3. Permissions & Scopes → enable `im:message` + `im:message:send_as_bot`
4. Event Subscription → set to **WebSocket mode** → add `im.message.receive_v1`
   - Requires at least one permission enabled first: 读取用户发给机器人的单聊消息 or 获取群组中用户@机器人消息
5. Publish a version
6. admin.feishu.cn → App Management → Enable the app

## Docs updated

- `README.md` — Quick Start now includes full Feishu setup inline
- `docs/feishu-app-setup.md` — full checklist + troubleshooting table
