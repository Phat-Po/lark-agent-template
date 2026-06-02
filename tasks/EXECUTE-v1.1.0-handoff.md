# EXECUTE — v1.1.0 sync (cards + persistent confirmation + timeout/errors)

> **Handoff for the next agent.** This is the execution-ready task doc. A prior agent
> already read both repos end-to-end, validated the approach, and resolved every
> structural unknown. **You do not need to re-investigate.** Read this doc top to bottom,
> then execute Step 0 → Step 8 in order.
>
> The companion brief `tasks/UPGRADE-2026-06-from-wpd.md` is the original porting spec
> (categorization, commit map, rationale). This doc supersedes it for *execution detail* —
> where they differ on concrete steps, follow **this** doc; consult the brief for *why*.

---

## 0. TL;DR

Port the upstream WPD Agent's **generic** harness wins into this public template and cut **v1.1.0**:

1. **Interactive Feishu cards** — replies render as CardKit v2 cards (colored header + markdown), text fallback on failure.
2. **lark-oapi SDK bug workarounds** — `_patch_ws_client_loop()` (uvicorn loop crash) + CARD-frame patch (dropped CARD messages).
3. **Button-based confirmation** — protected writes show 确认/取消 buttons; click confirms via `cardAction`; **pending action persisted in SQLite, looked up by `action_id`** (survives restart, multiple pending coexist, expiry handled).
4. **Timeout + error sanitization** — `with_timeout()` (15s) wraps Feishu API calls; failures always return a readable, sanitized message.

**Scope decision (already made, do not re-litigate):** v1.1.0 = 🟢 PORT only. **Defer** 🟡 Bitable + User OAuth + scheduled-automation to **v1.2**. Never port 🔴 WPD-specific data.

**Two design defaults already chosen:** (a) `BOT_DISPLAY_NAME` default = `"Lark Agent"`; (b) Bitable/OAuth deferred.

---

## 1. Critical context (read before touching code)

### 1.1 Repos
| Role | Path | Rule |
|---|---|---|
| **Target (this repo)** | `/Volumes/轻松打爆你/VIBE CODING/20_PROJECTS_MAINTAIN/20260526__python__lark-agent-template/` | edit here; public, MIT, currently v1.0.0 |
| **Upstream (reference)** | `/Volumes/轻松打爆你/VIBE CODING/10_PROJECTS_ACTIVE/20260521__python__wpd-agent/` | **READ-ONLY. Never modify.** Diff only. |

Diff upstream like: `WPD="/Volumes/轻松打爆你/VIBE CODING/10_PROJECTS_ACTIVE/20260521__python__wpd-agent"; git -C "$WPD" show <hash>`

### 1.2 The single most important structural finding
**Both repos use the same high-level `FeishuChannel` abstraction** (`from lark_oapi.channel import FeishuChannel`). The brief's "port the SDK patches verbatim" advice therefore holds — the patches operate on `lark_oapi.ws.client.Client`, which `FeishuChannel` drives internally, and `channel.on("cardAction", ...)` is supported. No raw-WSClient rewrite needed.

**One adaptation:** this template lazily creates `channel` *inside* `on_startup()` and only when credentials exist (setup-mode). Upstream creates it at module level. So in this repo the patches + `cardAction` registration must run **inside `on_startup()` after the channel is built**, guarded by the existing setup-mode branch. **Preserve setup-mode untouched** — it's a template feature (renders an HTML setup checklist when creds are missing).

### 1.3 This repo's layout differs from upstream (keep this repo's)
- Harness is already cleaned into `src/harness/` (`idempotency.py`, `metrics.py`, `result.py`, `schema.py`, `tracing.py`). **New generic harness modules go in `src/harness/`**, not `src/` root.
- Upstream still has duplicate `src/idempotency.py` / `src/metrics.py` / `src/tracing.py` and `src/tools/result.py` / `src/tools/schema.py` — **ignore those duplicates.**
- Tools use a decorator registry: `src/tools/registry.py` with `@register_tool(..., risk_level="read|write|destructive")`. `get_write_tool_names()` returns write+destructive names.

### 1.4 The template's confirmation model ≠ upstream's
- **Template (current):** the *agent* intercepts write tools in `_execute_tool_with_guards` (src/agent.py), stores an **in-memory** pending dict, and returns a `CONFIRM_REQUIRED` tool_error. Confirmation is via a **text** "confirm" reply (`CONFIRM_RE`). Tools have **no** `confirmed_by_user` parameter — the guard is agent-level.
- **Upstream:** tools self-gate via a `confirmed_by_user` arg + a policy that resolves member names → open_ids.
- **Your job:** keep the template's *agent-level guard* model, but upgrade the *store* from in-memory → **DB-backed (action_policy + db pending_actions)** and the *confirm UX* from text → **button card**. **Do NOT introduce `confirmed_by_user` into tool schemas** (would break `validate_tool_args` and is unnecessary here). **Do NOT port member/group resolution** (template has no social graph — args pass straight through).

### 1.5 Python / tests
- Host `python3` is **3.8** — too old. `python3.11` and `python3.12` exist at `/opt/homebrew/bin/`. Run tests in a venv: `/opt/homebrew/bin/python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install pytest && .venv/bin/python -m pytest -q`.
- CI runs pytest on 3.11/3.12 — keep it green.

---

## 2. Exact change set

### Step 0 — Branch + snapshot
```bash
cd "/Volumes/轻松打爆你/VIBE CODING/20_PROJECTS_MAINTAIN/20260526__python__lark-agent-template"
git status            # planning docs may already be committed; ensure clean
git checkout -b feat/v1.1-cards-confirm
```

### Step 1 — Card system (headline feature)

**ADD `src/card_builder.py`** — port from upstream `src/card_builder.py` (`git -C "$WPD" show 3d62120`). Keep `build_reply_card`, `build_confirm_card`, `build_error_card`. **Drop** `build_briefing_card` (briefing is WPD/deferred). Genericize: default title comes from config, not `"波波机"`:
```python
from lark_oapi.channel.card.builder import new_card
from src.config import BOT_DISPLAY_NAME

def build_reply_card(text: str, *, title: str | None = None, color: str = "blue") -> dict:
    card = new_card()
    card.config(wide_screen_mode=True)
    card.header(title=title or BOT_DISPLAY_NAME, template=color)
    card.markdown(content=text)
    return card.build().data
```
`build_confirm_card(text, tool_name, action_id, confirm_label="确认", cancel_label="取消")` — **must embed `action_id` in each button's `value`** exactly as upstream:
`action={"type":"button","value":{"action_id": action_id, "type":"confirm","tool": tool_name}}` (and `"type":"cancel"` for cancel). This is the contract the `cardAction` handler matches on.
`build_error_card(error_text)` — red header.

> ⚠️ **Verify the import path works** with the installed lark-oapi: `.venv/bin/python -c "from lark_oapi.channel.card.builder import new_card; print('ok')"`. If it fails, bump `lark-oapi>=1.4.0` in `requirements.txt` to whatever version upstream uses (`git -C "$WPD" grep lark-oapi -- requirements.txt`) and reinstall. This is the one genuine external-version risk in the whole task.

**MODIFY `src/config.py`** — add after the Feishu creds block:
```python
BOT_DISPLAY_NAME = os.environ.get("BOT_DISPLAY_NAME", "Lark Agent")
```

### Step 2 — Confirmation hardening (DB-persisted, button-driven)

**MODIFY `src/db.py`** — the `pending_actions` table is currently **single-slot** (PK `chat_id, sender_open_id`, no `action_id`, no `request_text`). Upgrade to upstream's **multi-row** form so multiple pending confirmations coexist and button-confirm survives restart.

Reference upstream `src/db.py`:
- Schema + migration: lines ~105–180 (`CREATE TABLE pending_actions` with `action_id` PK + `request_text`, index on `(chat_id, sender_open_id)`, and the in-place migration block that drops/recreates if the old single-slot schema is detected via `PRAGMA table_info`).
- Helpers: `save_pending_action` (now takes `action_id=`, `request_text=`; `ON CONFLICT(action_id) DO UPDATE`), `load_pending_action` (most-recent `ORDER BY created_at DESC LIMIT 1`, returns `action_id`+`request_text`), `take_pending_action_db` (SELECT+DELETE in one txn, no RETURNING — SQLite ≥3.24 compat), **NEW** `take_pending_action_by_action_id(action_id)`, **NEW** `delete_pending_action_by_action_id(action_id)`, **NEW** `sweep_expired_pending_actions(cutoff)`. Keep `delete_pending_action` and `clear_all_pending_actions`.

Port these helper bodies verbatim from upstream `src/db.py` lines 351–485 (they're already generic — no WPD data).

**ADD `src/action_policy.py`** — **GENERIC MECHANISM ONLY.** Port from upstream `src/action_policy.py` but **delete the entire social graph**:
- ❌ DELETE: `MEMBER_MAP`, `ALL_MEMBER_IDS`, `KNOWN_GROUPS`, `MEMBER_ALIASES`, `_TARGETED_MEMBER_TOOLS`, `_ALLOWED_ARGS`, all `_*_RE` member regexes, `is_authorized_sender`, `resolve_member_targets`, `resolve_message_recipient`, `is_allowed_message_recipient`, `message_expresses_member_scope`, and the member/recipient logic inside `normalize_proposed_action`.
- ✅ KEEP (generic): `PolicyError`, `PendingAction` dataclass, `PENDING_ACTION_TTL_SECONDS=1800`, `PENDING_ACTION_GRACE_SECONDS=86400`, `store_pending_action`, `take_pending_action`, `take_pending_action_by_id`, `clear_pending_action`, `clear_pending_action_by_id`, `clear_all_pending_actions`, `get_pending_action_id`, `_unique`. These delegate to the `src.db` helpers above.
- ✅ REPLACE `normalize_proposed_action` with a trivial generic canonicalizer (args pass straight through, just stable-serialize):
```python
def canonicalize_arguments(arguments_json: str) -> str:
    """Stable-serialize tool args so the stored payload replays deterministically.
    Generic template: no member resolution, no arg whitelist — pass through."""
    try:
        args = json.loads(arguments_json)
    except (json.JSONDecodeError, TypeError):
        return arguments_json
    return json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
```
- Fix the logger name: upstream uses `logging.getLogger("wpd.action_policy")` → use `"lark_agent.action_policy"`.

**MODIFY `src/agent.py`** — replace the in-memory pending store with the DB-backed flow:
- ❌ DELETE the in-memory block: `_pending_lock`, `_pending`, `_pending_key`, `_store_pending`, `_take_pending`, `_clear_pending` (lines ~69–95).
- ✅ Import from `src.action_policy`: `store_pending_action`, `take_pending_action`, `take_pending_action_by_id`, `clear_pending_action`, `get_pending_action_id`, `canonicalize_arguments`, `PolicyError`; and `from src.card_builder import build_confirm_card`; and `from src.db import load_pending_action`.
- ✅ `chat()` return type becomes `str | dict`. When the agent loop stored a pending action this turn, return a **confirm card dict**: `{"type": "card", "card": build_confirm_card(text=card_text, tool_name=..., action_id=...)}`. Pattern to follow: upstream `src/agent.py` lines 375–409 (`pending_row = load_pending_action(...)` → build `_build_confirm_text` → `build_confirm_card` → return dict). Keep it simple: no batch (`__batch__`) support needed for v1.1 — single pending action per turn is fine.
- ✅ Keep the existing **text-confirm** path working: when `_is_confirmation(user_message)` and a pending action exists, call new `execute_pending_action(...)` instead of the old in-memory replay.
- ✅ Change `_execute_tool_with_guards` (lines ~408–437): when `REQUIRE_WRITE_CONFIRMATION and name in write_tools`, instead of `_store_pending(...)` + returning `CONFIRM_REQUIRED` text, call `store_pending_action(chat_id, sender_open_id, name, canonicalize_arguments(arguments_json), request_text=...)` and still return a `CONFIRM_REQUIRED` tool_error so the loop stops cleanly — `chat()` then detects the stored row and emits the card. (The tool_error keeps the LLM loop from claiming false success.)
- ✅ ADD `execute_pending_action(pending_action, trace_id="", user_id="")` — generic single-tool version of upstream lines 836–861 (drop the `__batch__` branch): `result = await execute_tool(pending_action.tool_name, pending_action.arguments_json, trace_id=trace_id); return sanitize_reply(_format_tool_result(pending_action.tool_name, result))`. **Note:** template's `execute_tool` signature is `(name, arguments_json, trace_id="", message_id="")` — **no `user_id`** param; do not pass it.
- ✅ ADD `_expired_request_message(action)` — port upstream lines 616–621 (generic, no changes).
- ✅ ADD `_build_confirm_text(tool_name, arguments_json)` — a **generic** preview (tool name + a compact arg dump). Do NOT port upstream's per-tool emoji label map / member-count lines (WPD-shaped). Minimal generic version:
```python
def _build_confirm_text(tool_name: str, arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json)
    except (json.JSONDecodeError, TypeError):
        args = {}
    lines = [f"**Confirm action: `{tool_name}`**", ""]
    for k, v in args.items():
        sval = str(v)
        if len(sval) > 120:
            sval = sval[:120] + "…"
        lines.append(f"- **{k}**: {sval}")
    lines.append("")
    lines.append("Click 确认 to proceed, 取消 to cancel.")
    return "\n".join(lines)
```
- ✅ ADD `sanitize_reply(text)` — port upstream lines 648–653 (preserves lark_md; returns a fallback string if empty). Apply it to the final text reply path in `chat()`.
- ✅ System prompt: update `_DEFAULT_SYSTEM_PROMPT` to note the model may use Feishu-flavored markdown (lark_md) — bold, lists, links render in cards. Keep it generic/English+language-agnostic.

**MODIFY `src/main.py`** — wire cards, patches, and the card-action callback:
- Imports: `from src.card_builder import build_reply_card, build_confirm_card, build_error_card`; `from src.action_policy import take_pending_action_by_id, clear_pending_action_by_id`; `from src import agent` (already there).
- ADD module-level helpers (port from upstream `src/main.py`): `_patch_ws_client_loop()` (lines 45–56), `_patch_ws_client_card_handler()` (lines 75–137), `_verify_sdk_patches()` (lines 59–73), `MAX_CARD_SIZE=28000`, `_truncate_card_content()` (lines 143–157), `_send_card_with_fallback(chat_id, card, trace_id, fallback_text)` (lines 160–183), `_ensure_user_gets_response()` (lines 186–191). **Keep the explanatory docstrings on the two patches** — they teach the user *why* the monkey-patch exists. **Strip Chinese-only user strings to bilingual/English** where they're user-facing (e.g. the truncation suffix, the fallback error text).
  - ⚠️ These helpers reference `channel` and `metrics`. This repo imports metrics as `from src.harness import metrics` (upstream uses `from src import metrics`) — adjust. And `channel` is module-global but assigned in `on_startup`; the helpers run after startup so that's fine (they already do in upstream).
- `on_message` (lines 152–212): switch the reply path. Replace `await channel.send(chat_id, {"text": reply})` with the card flow — follow upstream lines 265–297: `agent.chat(...)` may return `str` or `{"type":"card","card":...}`; if dict, send that card; else `card_payload = build_reply_card(reply)`; send via `_send_card_with_fallback(chat_id, card_payload, trace_id, reply_text)`. Idempotent-hit replay and the error path also go through cards (lines 222–227, 296–297). Keep `complete_message/fail_message/complete_run/fail_run` calls intact.
- ADD `on_card_action(event)` — port upstream lines 304–376 **verbatim of logic** (translate user-facing Chinese strings to bilingual/English): parse `action.value` (handle the nested `value.get("value", value)`), branch on `type` confirm/cancel, on confirm `take_pending_action_by_id(action_id)` → handle `missing`/`expired`/`ready`, execute via `agent.execute_pending_action(...)`, on cancel `clear_pending_action_by_id(action_id)`. Guard all with try/except → `_ensure_user_gets_response`.
- Register the callback. In `on_startup`, **inside the non-setup branch after `channel` is created** (after line 244 `messaging.set_channel(channel)` / before `asyncio.create_task(channel.connect())`), add:
```python
channel.on("cardAction", on_card_action)
channel._ensure_bg_loop()
_patch_ws_client_loop()
_patch_ws_client_card_handler()
_verify_sdk_patches()
```
  (Upstream order: `_ensure_bg_loop()` → patch loop → patch card handler → verify. Match it.) The optional `_on_p2_card_action_trigger` logging wrapper (upstream 421–425) is nice-to-have; include only if trivial.

### Step 3 — Timeout + error sanitization
- **ADD `src/harness/timeout.py`** — port verbatim (it's 11 lines): `FEISHU_API_TIMEOUT_SECONDS = 15` and `async def with_timeout(coro, timeout=...)` wrapping `asyncio.wait_for`.
- **MODIFY `src/tools/messaging.py`** `send_message` (the outbound Feishu call at line ~45 `await _channel.send(...)`): wrap with `with_timeout(...)` and on `asyncio.TimeoutError` return a sanitized `api_error("The messaging API timed out. Please try again.")`. This is the concrete demonstration of the timeout story the README sells. The card sends in `main.py` already have `_send_card_with_fallback`; optionally wrap those too with `with_timeout` for completeness.

### Step 4 — OPTIONAL (DEFERRED — do nothing)
Bitable + User OAuth + scheduled-automation are **out of scope for v1.1.0**. Do not create `src/oauth.py`, `src/user_auth.py`, `src/tools/bitable.py`, `src/automation/`, or any `known_bitables`. Leave a one-line note in CHANGELOG "Planned for v1.2".

### Step 5 — Genericization pass (run BEFORE every commit)
```bash
grep -rni "wpd\|popo\|波波\|野生指挥部\|elaine\|鸿鸿\|futuretools\|serpapi\|38\.54\.88\.169\|PopoMachine" \
  --include=*.py --include=*.md --include=*.yml --include=*.example .
```
Must return **zero** hits in committed code/docs (a match inside this handoff doc or the brief is fine — those are planning artifacts; ideally exclude `tasks/`). Also confirm no real `open_id` (`ou_…`) / `chat_id` (`oc_…`) / base token / `cli_…` secret anywhere. Keep docs bilingual (README.md + README.zh.md). Keep the LLM layer provider-agnostic.

### Step 6 — Tests
ADD `tests/test_confirm.py` (run under python3.11 venv):
- **Pending-action persistence:** `init_db()` against a temp `DB_PATH`; `store_pending_action(...)` then `take_pending_action_by_id(action_id)` returns it once and `missing` the second time; an action with `expires_at` in the past returns status `expired`.
- **Timeout wrapper:** `with_timeout(asyncio.sleep(1), timeout=0.01)` raises `asyncio.TimeoutError`.
- **Card builder shape:** `build_confirm_card("t","create_doc","abc123")` returns a dict whose serialized form contains `"abc123"` inside a button `value`, has a header, and two buttons (确认/取消). `build_reply_card("hi")` returns a dict with header title == `BOT_DISPLAY_NAME` default.
- Keep existing `tests/test_harness.py` + `tests/test_registry.py` green.

Tip for DB tests: set `DB_PATH` via env or monkeypatch before importing `src.db`, or use the existing test pattern. Check how `src/db.py` resolves `DB_PATH` (from `src.config`) and override with `tmp_path`.

### Step 7 — Docs
- `README.md` + `README.zh.md`: add an **"Interactive Cards & Confirmation"** row to the feature/comparison table + a short section (screenshot optional/later).
- `docs/architecture.md`: document the card layer, the two SDK monkey-patches **and why**, the DB-persisted `action_id` confirmation flow, and the timeout wrapper.
- `docs/adding-tools.md`: note that any tool registered with `risk_level="write"|"destructive"` automatically gets the button-confirmation flow (no per-tool work needed).
- `.env.example`: add `BOT_DISPLAY_NAME=Lark Agent` with a one-line comment. Confirm every env var the app reads is present with a safe placeholder.
- `tasks/STATUS.md`: append a v1.1.0 entry (features + any new gotchas).
- `docs/onboarding-prompt.md`: step count is **unchanged** (no new OAuth scopes shipped) — only touch if something else changed.

### Step 8 — Version + changelog
- `pyproject.toml`: bump version → `1.1.0`.
- ADD `CHANGELOG.md`: v1.1.0 entry — interactive cards, lark-oapi SDK fixes (uvicorn loop + CARD frame), DB-persisted button confirmation, timeout/error sanitization; note Bitable/OAuth planned for v1.2.

---

## 3. Verification before reporting done (acceptance checklist)
- [ ] `.venv/bin/python -m pytest -q` green (3.11). CI mirrors 3.11/3.12.
- [ ] `.venv/bin/python -c "import src.main, src.agent, src.card_builder, src.action_policy, src.harness.timeout"` imports clean.
- [ ] `build_reply_card` import path works against installed lark-oapi (bump requirement if not).
- [ ] Genericization grep (§Step 5) → zero hits outside `tasks/`.
- [ ] Secret/ID grep → zero real credentials/ids.
- [ ] Both READMEs updated; `.env.example` complete; `pyproject.toml` == 1.1.0; `CHANGELOG.md` + `tasks/STATUS.md` updated.
- [ ] Reply path returns a card with text fallback; protected write returns a 确认/取消 card; confirm executes; pending action persisted by `action_id` (survives restart); expired handled.

## 4. Hard guardrails (non-negotiable)
- **Never modify the upstream WPD repo** — read-only diffs only.
- **No real credentials/identifiers** in code, docs, examples, screenshots.
- **Do NOT `git push` or `gh release` without explicit operator confirmation.** When ready, stop and ask, verbatim: *"Ready to push to main. This will publish the public v1.1.0 release. Confirm?"* — then wait for an explicit "yes".
- Port **mechanism**, delete **social-graph data**. If you find yourself copying an `ou_…`/`oc_…`, stop — that's a WPD-specific line.
- This repo's clean `src/harness/` layout wins over upstream's duplicate `src/`-root modules.

## 5. Release (only after operator confirms — do not run unprompted)
```bash
git tag v1.1.0
git push origin main
git push origin v1.1.0
gh release create v1.1.0 --repo Phat-Po/lark-agent-template \
  --title "v1.1.0 — Interactive cards & persistent confirmation" \
  --notes "<changelog>"
```

---

### Appendix — upstream commit / line map
```
Card builder      : src/card_builder.py            (commit 3d62120)  → port reply/confirm/error
SDK patches       : src/main.py  lines 45–137      (096a735 6f5086b 89ac771 8286690)
Card send+fallback: src/main.py  lines 140–191
on_card_action    : src/main.py  lines 304–376     (c00b6c3 0e96b6a)
chat()→card       : src/agent.py lines 375–409
execute_pending   : src/agent.py lines 836–861     (drop __batch__)
_expired_message  : src/agent.py lines 616–621
sanitize_reply    : src/agent.py lines 648–653
action_policy     : src/action_policy.py           (strip MEMBER_MAP/resolve_*; keep store/take/expire)
db pending helpers: src/db.py    lines 105–180 (schema+migration), 351–485 (helpers)
timeout           : src/harness/timeout.py
Full range        : git -C "$WPD" log --oneline f9f8a98..ea31cb9
```
