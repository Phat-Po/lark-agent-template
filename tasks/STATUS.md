# Project Status — lark-agent-template

## Current State

**Status**: Stable / Maintain
**Last active**: 2026-06-02
**Release**: v1.1.0 (pending push)

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

---

## [2026-06-02] | v1.1.0 implemented (pending push)

**Status**: Code complete, tests green (36/36), awaiting operator approval to push.

**New features:**
- **Interactive Feishu cards** — replies render as CardKit v2 cards (colored header + markdown). Text fallback on card send failure.
- **lark-oapi SDK bug workarounds** — `_patch_ws_client_loop()` fixes uvicorn loop crash; `_patch_ws_client_card_handler()` fixes dropped CARD messages.
- **DB-persisted button confirmation** — protected writes show 确认/取消 buttons. Pending action stored in SQLite by `action_id` (survives restart, multiple pending coexist, 30-min expiry).
- **Timeout + error sanitization** — `with_timeout()` (15s) wraps Feishu API calls. Failures return sanitized messages.

**Files changed:**
- `src/card_builder.py` — new: build_reply_card, build_confirm_card, build_error_card
- `src/action_policy.py` — new: generic pending-action store (no social graph)
- `src/harness/timeout.py` — new: async timeout wrapper
- `src/config.py` — added BOT_DISPLAY_NAME
- `src/db.py` — migrated pending_actions to multi-row schema (action_id PK)
- `src/agent.py` — DB-backed confirm flow, sanitize_reply, _build_confirm_text
- `src/main.py` — card send path, SDK patches, on_card_action handler
- `src/tools/messaging.py` — timeout-wrapped send_message
- `tests/test_confirm.py` — new: persistence, timeout, card builder tests
- Docs: README.md, README.zh.md, architecture.md, adding-tools.md, .env.example

**Deferred to v1.2:**
- Bitable tools + User OAuth + scheduled-automation (per handoff doc scope decision).

**Gotchas:**
- lark-oapi>=1.4.0 required for `lark_oapi.channel.card.builder.new_card` import.
- The two SDK monkey-patches are logged at startup; if either shows `sdk_patch_MISSING`, check lark-oapi version.
