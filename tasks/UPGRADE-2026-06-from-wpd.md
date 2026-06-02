# Upgrade Brief — Sync `lark-agent-template` with upstream WPD Agent (2026-06)

> **For the agent working in this repo.** This is a porting brief, not a finished change.
> Read it top to bottom, then execute the steps in order. Do **not** push to GitHub until
> the human operator explicitly confirms (see "Hard guardrails").

## 摘要（给操作者）

这个模板是 2026-05-26 从上游 WPD Agent 抽取出来的「干净通用版」，当时停在 *harness 完成* 状态。
之后上游又做了四块工作：**消息卡片系统**、**确认流程加固**、**超时/错误净化**、**多维表格 + 用户 OAuth**。
本文件告诉模板这边的 agent：**新增了什么**、**哪些该搬过来 / 哪些可选 / 哪些跳过**、**怎么搬**、
以及**改完怎么发布到 public 让别人直接 clone 就能用**。目标是发一个 **v1.1.0**。

---

## 1. Context — what this repo is vs. where upstream went

| | Repo | State |
|---|---|---|
| **Upstream (source of truth, READ-ONLY)** | `/Volumes/轻松打爆你/VIBE CODING/10_PROJECTS_ACTIVE/20260521__python__wpd-agent/` | Private production bot (WPD / 波波机 PopoMachine). Advanced past the fork point. |
| **This repo (target)** | `/Volumes/轻松打爆你/VIBE CODING/20_PROJECTS_MAINTAIN/20260526__python__lark-agent-template/` | Public, generic, MIT. GitHub `Phat-Po/lark-agent-template`, currently **v1.0.0**. |

**Fork point:** this template was extracted at upstream's harness-complete state on **2026-05-26**
(upstream commits `35cce47` / `19fc03e`, validated through `f9f8a98`). Everything upstream
committed *after* that is candidate work for this upgrade.

**Methodology already established** (do not re-invent it): upstream's
`docs/agent-template-guide.md` defines which modules are **generic harness** (`src/harness/*`,
`src/db.py`, `src/tool_risk.py`, `src/config.py`, `src/logging_utils.py`) vs **WPD-specific**
(`src/agent.py` social logic, `src/action_policy.py` member/group maps, `src/briefing.py`,
WPD tool data). Keep that boundary. When you port, generic mechanism comes in, WPD data stays out.

**Structural note:** this template already cleaned the harness into `src/harness/`
(`idempotency.py`, `metrics.py`, `result.py`, `schema.py`, `tracing.py`) and uses a
decorator-based `src/tools/registry.py`. Upstream still carries some duplicate `src/`-level
copies (`src/idempotency.py`, `src/metrics.py`, `src/tracing.py`) — **ignore those duplicates**
and keep this repo's clean `harness/` layout. New generic modules go into `src/harness/` where
they belong, not at `src/` root.

---

## 2. What's new upstream — categorized (PORT / OPTIONAL / SKIP)

### 🟢 PORT — generic harness wins, belong in the public template (this is the v1.1.0 scope)

| Block | New / changed files (upstream) | Key commits | Why it belongs in a public template |
|---|---|---|---|
| **Interactive message cards** | `src/card_builder.py` (NEW), changes in `src/main.py`, `src/agent.py` | `3d62120` `9cfcc8a` `f2dd0f2` `c00b6c3` `a1ad82d` | Replies render as Feishu **CardKit v2** cards (colored header, markdown) instead of plain text. Flagship UX upgrade — directly visible to every user. |
| **lark-oapi SDK fixes (uvicorn + CARD drop)** | `_patch_ws_client_loop()` and the CARD-frame patch in `src/main.py` | `096a735` `6f5086b` `89ac771` `8286690` | Two real upstream-SDK bugs: (a) `WSClient.start()` uses a module-level loop that dies under uvicorn; (b) CARD messages were silently dropped by `_handle_data_frame`. **Anyone** running this stack hits these. High value, generic. |
| **Button-based confirmation (cardAction callback)** | confirm card in `src/card_builder.py` (`build_confirm_card`), cardAction handler in `src/main.py`, DB `pending_actions` lookup | `c00b6c3` `0e96b6a` | Risky writes show 确认 / 取消 buttons; clicking confirms via `cardAction`. Pairs with the harness's existing `confirmed_by_user` gate. |
| **Confirmation-flow hardening (mechanism only)** | `src/action_policy.py` (NEW — port the *mechanism*, not the data), DB pending-action persistence | `8e9f40d` `0e96b6a` `934c00b` `add4fa5` `a8a8b2c` `ea31cb9` | Persist pending actions to SQLite (survives restart / works across local↔server), support **multiple/batched** pending confirmations, false-success guard, expiry UX, "policy canonicalizes, never rejects" write flow, raised tool-loop cap. All generic reliability. |
| **Timeout + error sanitization** | `src/harness/timeout.py` (NEW), error handling in `src/main.py` / tools | `f9f8a98` `e10ff1c` | `with_timeout()` wraps Feishu API calls (15s); errors are sanitized before reaching the user; "error feedback guarantee" so failures never hang silently. Generic harness reliability. |
| **System prompt → lark_md** | `src/agent.py` prompt + `sanitize_reply` preserves markdown | `9cfcc8a` | Makes the model emit Feishu-flavored markdown that the cards render correctly. Generic. |

### 🟡 OPTIONAL — genuinely useful but adds setup friction; ship as an **opt-in example**, not default-on

| Block | Files (upstream) | Why optional |
|---|---|---|
| **Bitable (多维表格) read/write tool** | `src/tools/bitable.py` (NEW), `src/known_bitables.py` (NEW — **WPD base IDs, do NOT port**) | A generic "read/write a Feishu Bitable" tool is attractive. But it needs **user OAuth** (below) and the upstream version hardcodes WPD base tokens. If included: ship as `examples/` tool, document the extra OAuth scopes, and require the user to supply their own base IDs via env. |
| **User OAuth (write-as-user)** | `src/oauth.py` (NEW), `src/user_auth.py` (NEW), `oauth_router` in `src/main.py` | Adds a redirect-URI + token-store setup step. Worth it only for tools that must act as the user (Bitable write). Keep out of the 5-minute happy path. |
| **Scheduled automation example** | `src/automation/` (`daily_report.py`, `reminders.py`), `src/briefing.py` | This repo has **no** `automation/` yet. A *generic* "daily scheduled message" example (APScheduler is already a dep) would showcase the scheduler. The upstream version is hardwired to FutureTools/SerpAPI — strip that; ship a minimal generic cron-message example only. |

### 🔴 SKIP — WPD-specific, must never enter the public template

- `MEMBER_MAP`, `ALL_MEMBER_IDS`, `MEMBER_ALIASES`, `KNOWN_GROUPS` in `src/action_policy.py`
  — real Feishu `open_id`s, the 野生指挥部 `chat_id`, and names (Popo / Elaine / 波波 / 鸿鸿酱).
- "我和X" / "帮大家" member-combo resolution (`_ALL_SCOPE_RE`, targeted-member tools) — WPD social graph.
- `src/known_bitables.py` content (WPD base/table tokens).
- Daily-briefing source logic (FutureTools.io / SerpAPI schedule, the Tue–Sat/Sun–Mon table).
- Any string: `WPD`, `Wild Products Dept`, `波波机`, `PopoMachine`, `野生指挥部`, `Popo`, `Elaine`,
  the VPS IP `38.54.88.169`, and the briefing API keys.

---

## 3. How to operate — step by step

> Work on a branch. Snapshot first. Read the upstream diff for each block before porting.

### Step 0 — Prep
```bash
cd "/Volumes/轻松打爆你/VIBE CODING/20_PROJECTS_MAINTAIN/20260526__python__lark-agent-template"
git status            # must be clean; if not, commit a snapshot first
git checkout -b feat/v1.1-cards-confirm
```
To read any upstream change, diff it directly from the source repo, e.g.:
```bash
WPD="/Volumes/轻松打爆你/VIBE CODING/10_PROJECTS_ACTIVE/20260521__python__wpd-agent"
git -C "$WPD" show 3d62120          # see the card-builder commit
git -C "$WPD" log --oneline f9f8a98..ea31cb9   # full candidate range
```

### Step 1 — Port the card system (the headline feature)
1. Copy `src/card_builder.py` from upstream. **Genericize:** the default `title="波波机"` →
   pull the app/bot display name from config (add `BOT_DISPLAY_NAME` to `config.py` + `.env.example`,
   default e.g. `"Lark Agent"`). Keep `build_reply_card`, `build_confirm_card`, `build_error_card`,
   and the briefing card builder (rename/strip any WPD wording).
2. In `src/main.py`, port `_patch_ws_client_loop()` **and** the CARD-frame patch verbatim
   (these are SDK-bug workarounds — keep the explanatory docstrings; they teach the user why).
3. Switch the reply path from text send → `channel.send(chat_id, {"card": payload})` with a
   **text fallback** if card send fails (upstream `a1ad82d` has the fallback + truncation + metrics).
4. Port the `lark_md` system-prompt change and `sanitize_reply` markdown preservation from `src/agent.py`
   (generic parts only — drop any member/group references).

### Step 2 — Port confirmation hardening (mechanism, not data)
1. Create `src/action_policy.py` in this repo with **only the generic mechanism**:
   pending-action create/load/take/expire, canonicalization, batch support, the
   "canonicalize never reject" write flow. **Delete** `MEMBER_MAP` / `KNOWN_GROUPS` / `MEMBER_ALIASES`
   / member-combo resolution. Where upstream resolves a member name → `open_id`, the template should
   instead pass arguments straight through (the template has no social graph).
2. Add the `pending_actions` table + helpers to `src/db.py` (upstream `aa14809` `0e96b6a` —
   `save/load/take/delete pending_action`, `take_pending_action_by_action_id`,
   `clear_all_pending_actions`). This is what makes button-confirm survive restarts.
3. Wire the `cardAction` callback handler in `src/main.py`: look up the pending action by
   `action_id` **from the DB** (not an in-memory dict), execute on 确认, clear on 取消, and
   guard against false-success / double-execution.
4. Keep it tied to the harness's existing `confirmed_by_user` convention and `tool_risk.py`
   `PROTECTED_WRITE_TOOLS` classification (already in this repo).

### Step 3 — Port timeout + error sanitization
1. Add `src/harness/timeout.py` (the 10-line `with_timeout` wrapper, `FEISHU_API_TIMEOUT_SECONDS = 15`).
2. Wrap outbound Feishu API calls with it. Port the error-sanitization + "always send the user a
   readable error" behavior (upstream `e10ff1c`). This belongs in the harness story the README sells.

### Step 4 — OPTIONAL: Bitable + OAuth + scheduled example
Only if the operator wants them in v1.1 (recommendation: defer to **v1.2** to keep v1.1 focused).
If included: put the Bitable tool under `examples/`, require user-supplied base IDs via env,
document the extra OAuth scopes and redirect URI in `docs/feishu-app-setup.md`, and add a
**generic** scheduled-message example (strip FutureTools/SerpAPI entirely).

### Step 5 — Genericization pass (run before every commit)
- Grep the whole repo for WPD identifiers and remove every hit:
  ```bash
  grep -rni "wpd\|popo\|波波\|野生指挥部\|elaine\|鸿鸿\|futuretools\|serpapi\|38\.54\.88\.169" \
    --include=*.py --include=*.md --include=*.yml --include=*.example .
  ```
- Confirm no real `open_id` / `chat_id` / base token / API key is present anywhere.
- Keep docs **bilingual** (update both `README.md` and `README.zh.md`).
- Keep the LLM layer **provider-agnostic** (OpenAI-compatible). Cards/confirmation must not
  assume a specific provider.

### Step 6 — Tests
- Extend `tests/test_harness.py`: pending-action persistence (save → take → expire),
  timeout wrapper raises on expiry.
- Add a card-builder test: `build_reply_card` / `build_confirm_card` return well-formed dicts
  with the right header/buttons and the `action_id` embedded in button `value`.
- Keep CI green (GitHub Actions, Python 3.11/3.12).

### Step 7 — Docs
- `README.md` + `README.zh.md`: add an **"Interactive Cards & Confirmation"** feature row to the
  comparison table; add a short section + (later) a screenshot.
- `docs/architecture.md`: document the card layer, the SDK monkey-patches (and *why*), the
  DB-persisted pending-action confirmation flow, and the timeout wrapper.
- `docs/adding-tools.md`: show how a write tool opts into button confirmation via `confirmed_by_user`.
- `.env.example`: add any new vars (`BOT_DISPLAY_NAME`, optional OAuth/Bitable vars).
- `tasks/STATUS.md`: bump to v1.1.0, note new features + any new gotchas.
- `docs/onboarding-prompt.md`: if setup steps changed (e.g. OAuth redirect URI), update the
  step list and the step-count.

### Step 8 — Version + changelog
- Bump version in `pyproject.toml` to `1.1.0`.
- Add a `CHANGELOG.md` entry (create the file if absent): cards, SDK fixes, DB-persisted
  confirmation, timeout/error handling.

---

## 4. Making it public so others can clone & run directly

The repo is **already public** (`Phat-Po/lark-agent-template`, v1.0.0). For v1.1.0 the job is a
clean, safe re-release — not a first-time publish. Checklist:

1. **Secret scan must return zero credentials** (variable names are fine, real values are not):
   ```bash
   grep -rn "sk-\|Bearer\|password\|secret\|token\|cli_\|ou_\|oc_\|cli_a" \
     --include=*.py --include=*.md --include=*.yml --include=*.example .
   ```
   Plus the WPD-identifier grep from Step 5. Both must be clean.
2. **`.env.example` is the contract.** Every var the app reads must appear there with a safe
   placeholder and a one-line comment. A new user should be able to fill only `LARK_APP_ID`,
   `LARK_APP_SECRET`, `LLM_API_KEY` (+ provider base URL) and get a working bot. New card/confirm
   features must **degrade gracefully** with default env (no extra setup to get a reply).
3. **`.env`, `data/*.db*` must stay out of git** (verify `.gitignore`). If `data/agent.db*`
   was ever committed, remove from index: `git rm --cached data/agent.db*`.
4. **5-minute path still works:** `docker compose run --rm agent` → credential prompt → bot replies
   (now with a card). Re-validate the entrypoint credential flow didn't break.
5. **README freshness:** comparison table, feature list, and any screenshots reflect cards +
   confirmation. Regenerate `marketing/screenshots/` if the reply UI changed materially.
6. **Onboarding prompt** (`docs/onboarding-prompt.md`) reflects the current step count and any
   new scopes (only if OPTIONAL OAuth/Bitable shipped).
7. **Tag + release** (only after operator confirms — this is the public-facing push):
   ```bash
   git tag v1.1.0
   git push origin main
   git push origin v1.1.0
   gh release create v1.1.0 --repo Phat-Po/lark-agent-template \
     --title "v1.1.0 — Interactive cards & persistent confirmation" \
     --notes "<changelog>"
   ```

---

## 5. Acceptance checklist (definition of done for v1.1.0)

- [ ] Replies render as Feishu cards; text fallback works if card send fails.
- [ ] Bot runs under uvicorn without the WSClient loop crash; CARD frames are received.
- [ ] A protected write shows 确认/取消 buttons; clicking 确认 executes; works after a restart
      (pending action persisted in SQLite, looked up by `action_id`).
- [ ] Multiple pending confirmations don't collide; expired confirmations are handled cleanly.
- [ ] Feishu API calls are timeout-wrapped; failures return a readable, sanitized message.
- [ ] `grep` for WPD identifiers and for real credentials/IDs → **zero** hits.
- [ ] Both `README.md` and `README.zh.md` updated; `.env.example` complete; CI green.
- [ ] `pyproject.toml` = 1.1.0; `CHANGELOG.md`, `tasks/STATUS.md` updated.
- [ ] Fresh-clone 5-minute path verified with default `.env`.

---

## 6. Hard guardrails

- **Never modify the upstream WPD repo.** It is read-only reference.
- **No real credentials or identifiers** in code, docs, examples, or screenshots —
  no `open_id`/`chat_id`/base token/API key/VPS IP.
- **Keep docs bilingual** and the LLM layer **provider-agnostic**.
- **Do not `git push` or `gh release` without explicit operator confirmation.** Required phrasing:
  "Ready to push to main. This will deploy / publish the public release. Confirm?"
- When porting `action_policy.py`, port the **mechanism**, delete the **social-graph data**.
  If you find yourself copying an `open_id`, stop — that's the WPD-specific line.

---

### Appendix — upstream commit map (read these to see exact diffs)

```
Cards / SDK fixes : 3d62120 9cfcc8a f2dd0f2 c00b6c3 017f9f3 a1ad82d
                    096a735 6f5086b 89ac771 8286690 a13a864 cddc4ea
Timeout / errors  : f9f8a98 e10ff1c
Confirm hardening : 8e9f40d 0e96b6a e4ac150 934c00b 27a58da
                    add4fa5 2de7863 a8a8b2c ea31cb9
Bitable / OAuth   : 5d7eac9 aee0bc0 5088fc9 088480a bcf3bd1   (OPTIONAL)
Full range        : git -C <wpd> log --oneline f9f8a98..ea31cb9
```
