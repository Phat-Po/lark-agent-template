# Onboarding Prompt

Paste the block below into any AI assistant (Claude, ChatGPT, Cursor, etc.) to get guided through the full setup. The AI will ask where you are and skip completed steps.

---

```markdown
# Lark Agent Template — Setup Guide

You are helping me set up **lark-agent-template**, an open-source Feishu/Lark AI bot with tool calling.
Repo: https://github.com/Phat-Po/lark-agent-template

## Step 0: Ask where I am

Before doing anything, ask me which of these steps I've already completed:

1. Feishu app created (have App ID + App Secret)
2. Bot capability enabled
3. Permissions & Scopes added
4. Event Subscription configured (WebSocket + im.message.receive_v1)
5. App published & enabled in admin console
6. Repo cloned and .env configured
7. Bot running (Docker or Python)
8. Bot responding to messages in Feishu

Ask: "Which step number are you at? (1-8, or describe what you've done so far)"
Then skip to that step and continue from there.

---

## Step 1: Create Feishu App

1. Go to https://open.feishu.cn/
2. Click **Create App** -> **Enterprise Custom App**
3. Fill in app name and description
4. Go to **Credentials & Basic Info** -> copy **App ID** and **App Secret** (save these, you'll need them for .env)

## Step 2: Enable Bot Capability

1. Go to **Add App Capability**
2. Find **Bot** -> click **Enable**
3. Without this, the bot won't appear in Feishu search

## Step 3: Add Permissions & Scopes

Go to **Permissions & Scopes** and enable ALL of the following:

```json
{
  "scopes": {
    "tenant": [
      "calendar:calendar",
      "calendar:calendar.acl:create",
      "calendar:calendar.acl:delete",
      "calendar:calendar.acl:read",
      "calendar:calendar.event:create",
      "calendar:calendar.event:delete",
      "calendar:calendar.event:read",
      "calendar:calendar.event:reply",
      "calendar:calendar.event:update",
      "calendar:calendar.free_busy:read",
      "calendar:calendar:create",
      "calendar:calendar:delete",
      "calendar:calendar:read",
      "calendar:calendar:readonly",
      "calendar:calendar:subscribe",
      "calendar:calendar:update",
      "contact:user.base:readonly",
      "docs:document.content:read",
      "docs:document:copy",
      "docs:document:export",
      "docs:document:import",
      "docx:document",
      "docx:document:create",
      "docx:document:readonly",
      "docx:document:write_only",
      "drive:drive",
      "drive:drive.metadata:readonly",
      "drive:drive.search:readonly",
      "drive:drive:readonly",
      "drive:file",
      "drive:file:download",
      "drive:file:readonly",
      "drive:file:upload",
      "im:chat",
      "im:chat.members:read",
      "im:chat.members:write_only",
      "im:chat:read",
      "im:chat:readonly",
      "im:message",
      "im:message.group_at_msg:readonly",
      "im:message.p2p_msg:readonly",
      "im:message:readonly",
      "im:message:send_as_bot",
      "im:resource",
      "search:docs:read",
      "task:attachment:read",
      "task:attachment:write",
      "task:comment",
      "task:comment:read",
      "task:comment:readonly",
      "task:comment:write",
      "task:custom_field:read",
      "task:custom_field:write",
      "task:section:read",
      "task:section:write",
      "task:task",
      "task:task:read",
      "task:task:readonly",
      "task:task:write",
      "task:task:writeonly",
      "task:tasklist:read",
      "task:tasklist:write"
    ]
  }
}
```

This covers ALL built-in tools (calendar, tasks, docs, drive, messaging, search).
Copy-paste the scope names one by one into the search box in Feishu's permission page and enable each.

## Step 4: Configure Event Subscription

1. Go to **Event Subscription**
2. Under **Subscription Method**, select **Use long connection to receive events (WebSocket)**
3. Click **Add Event** -> search for and add `im.message.receive_v1`
4. Feishu will require at least one of these to be enabled first:
   - **读取用户发给机器人的单聊消息** (receive DMs)
   - **获取群组中用户@机器人消息** (receive @mentions in groups)
5. Confirm these show **已开通** (Enabled) in Permissions & Scopes, then return to finish adding the event

## Step 5: Publish & Enable

1. Go to **Version Management & Publish** -> **Create a version**
2. Fill in version notes -> **Submit**
3. If you are the enterprise admin, approve immediately
4. Go to https://admin.feishu.cn -> **App Management** -> find your app -> **Enable**

## Step 6: Clone & Configure

```bash
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|----------|----------------|
| `LARK_APP_ID` | Feishu app Credentials page |
| `LARK_APP_SECRET` | Feishu app Credentials page |
| `LLM_API_KEY` | Your LLM provider (OpenAI/DeepSeek/Mimo/etc.) |
| `LLM_BASE_URL` | Your LLM provider's API base URL |
| `LLM_MODEL` | Model name (e.g. gpt-4o, deepseek-chat) |

Optional:
| `SEARCH_API_KEY` | SerpAPI key (only if you want web search tool) |

**IMPORTANT**: Do NOT skip this step. The bot will crash-loop without valid `LARK_APP_ID` and `LARK_APP_SECRET`. If you see `FeishuChannel requires app_id and app_secret` in the logs, come back and fill in `.env`.

## Step 7: Run the Bot

**With Docker (recommended):**
```bash
docker compose up --build
```

**Without Docker (Python 3.11+ required):**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

Look for this in the logs:
```
Lark Agent Template started
  Tools: 15 loaded
connected to wss://msg-frontier.feishu.cn/ws/v2 ...
```

## Step 8: Test the Bot

Search for your app name in Feishu and send it a message. Try these:

| Test | Send | Expected |
|------|------|----------|
| Basic reply | "Hello" | Bot responds with a greeting |
| Calendar | "What's on my calendar today?" | Bot reads calendar events |
| Tasks | "Create a task: buy milk" | Bot creates a Feishu task |
| Docs | "Search docs: project plan" | Bot searches documents |
| Web search | "Search: 2026 AI trends" | Bot returns search results (needs SEARCH_API_KEY) |

If the bot doesn't respond, check:
- App is enabled in admin.feishu.cn
- Event subscription has `im.message.receive_v1` added
- WebSocket mode is selected (not webhook)
- .env credentials are correct
- Bot is running (check terminal/logs for errors)

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot not found in search | Bot capability not enabled | Step 2 |
| WebSocket connects but no messages | Event not subscribed | Step 4 |
| Bot found but doesn't respond | App not enabled in admin | Step 5 |
| Permission denied errors | Missing scope | Step 3 — add the missing scope |
| "Python version" errors | System python is 3.8 | Use Docker, or install Python 3.11+ |
| "Module not found" errors | Dependencies not installed | Run `pip install -r requirements.txt` |
```
