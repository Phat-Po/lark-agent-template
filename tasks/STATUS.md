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

---

## [2026-06-02] | v1.1.0 upgrade planned & handed off (not yet executed)

**Done this session:**
- Read the full upgrade brief (`tasks/UPGRADE-2026-06-from-wpd.md`) and investigated both the template and the upstream WPD repo end-to-end (read-only).
- Produced a decision-complete, execution-ready task doc: **`tasks/EXECUTE-v1.1.0-handoff.md`** (the next agent executes from this).
- No source code changed.

**Key findings (resolved unknowns so the next agent need not re-investigate):**
- Both repos use the same `FeishuChannel` abstraction → the upstream SDK monkey-patches (`_patch_ws_client_loop`, CARD-frame patch) and `channel.on("cardAction")` port cleanly.
- This repo creates `channel` lazily inside `on_startup()` (setup-mode) → patches + cardAction registration must run inside startup after channel creation; preserve setup-mode.
- Template's `pending_actions` table is single-slot (PK chat_id+sender) → must migrate to upstream's multi-row schema keyed by `action_id` (+ `request_text`) for persistent button-confirm.
- Template guards writes at the agent level (no `confirmed_by_user` in tool schemas) → port the DB-backed store + button card, but do NOT add `confirmed_by_user` and do NOT port member/group resolution (no social graph).
- Host `python3` is 3.8; use `/opt/homebrew/bin/python3.11` venv for tests.

**Current state:**
- v1.0.0 on `main`, repo otherwise stable. Planning docs committed as a snapshot. No branch created yet.

**Next steps:**
1. Execute `tasks/EXECUTE-v1.1.0-handoff.md` Step 0 → Step 8 on branch `feat/v1.1-cards-confirm`.
2. v1.1.0 scope = 🟢 cards + SDK fixes + DB-persisted button confirmation + timeout/errors. Defer Bitable/OAuth/scheduled to v1.2.
3. Stop and ask the operator before any `git push` / `gh release`.

**Decisions / notes:**
- `BOT_DISPLAY_NAME` default = `"Lark Agent"`.
- Upstream repo is READ-ONLY reference — never modify it.
