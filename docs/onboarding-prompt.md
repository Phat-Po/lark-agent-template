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

## Step 8: Enable All Permissions

Even though the bot is running, the tools won't work without the right permissions. Go to your Feishu app → **Permissions & Scopes** and enable ALL of these:

### Required for messaging (enable first)

| Scope | What it does |
|-------|-------------|
| `im:message` | Receive and send messages |
| `im:message:send_as_bot` | Send messages as bot identity |
| `im:message:readonly` | Read message content |
| `im:message.p2p_msg:readonly` | Read direct messages |
| `im:message.group_at_msg:readonly` | Read group @mentions |

### Calendar tools

| Scope | What it does |
|-------|-------------|
| `calendar:calendar` | Access calendars |
| `calendar:calendar:read` | List calendars |
| `calendar:calendar:readonly` | Read calendar info |
| `calendar:calendar.event:read` | List/read events |
| `calendar:calendar.event:create` | Create events |
| `calendar:calendar.event:delete` | Delete events |
| `calendar:calendar.event:update` | Update events |
| `calendar:calendar.free_busy:read` | Read free/busy status |

### Task tools

| Scope | What it does |
|-------|-------------|
| `task:task` | Full task access |
| `task:task:read` | Read tasks |
| `task:task:write` | Create/update/delete tasks |
| `task:tasklist:read` | Read task lists |
| `task:tasklist:write` | Manage task lists |
| `task:comment:read` | Read task comments |
| `task:comment:write` | Write task comments |

### Document & Drive tools

| Scope | What it does |
|-------|-------------|
| `docx:document` | Full document access |
| `docx:document:readonly` | Read documents |
| `docx:document:create` | Create documents |
| `docs:document.content:read` | Read document content |
| `drive:drive` | Full drive access |
| `drive:drive:readonly` | List/read drive files |
| `drive:drive.search:readonly` | Search documents |
| `drive:file:readonly` | Read file metadata |
| `drive:file:download` | Download files |

### After enabling scopes

1. Go to **Version Management** → **Create a version** → **Submit**
2. If you are the admin, approve the version
3. Go to **admin.feishu.cn** → **App Management** → ensure app is **Enabled**

Without publishing a new version, the new scopes won't take effect.

---

## Step 9: Test the Bot

Search for your app name in Feishu and send it a message. Try these tests in order:

### Basic (no extra permissions needed)

| Send | Expected result |
|------|----------------|
| `Hello` | Bot responds with a greeting |
| `What can you do?` | Bot lists its capabilities |

### Calendar (needs calendar scopes)

| Send | Expected result |
|------|----------------|
| `What's on my calendar today?` | Bot reads and lists today's events |
| `Create a meeting tomorrow at 3pm called "Team Sync"` | Bot creates a calendar event |

### Tasks (needs task scopes)

| Send | Expected result |
|------|----------------|
| `What tasks do I have?` | Bot lists your open tasks |
| `Create a task: buy milk` | Bot creates a Feishu task |

### Documents (needs doc/drive scopes)

| Send | Expected result |
|------|----------------|
| `Search docs: project plan` | Bot searches your documents |
| `Create a document called "Meeting Notes"` | Bot creates a new doc |

### Web search (needs SEARCH_API_KEY in .env)

| Send | Expected result |
|------|----------------|
| `Search web: AI news 2026` | Bot returns web search results |

### If a test fails

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot doesn't reply at all | Event subscription missing | Step 4 — add `im.message.receive_v1` |
| "permission denied" or "scope" error | Missing a permission scope | Go back to Step 8, add the missing scope, publish new version |
| "API key not configured" | SEARCH_API_KEY not set | Add to `.env`, restart bot |
| Bot replies but tool fails silently | Scope enabled but not published | Create and publish a new app version |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot not found in search | Bot capability not enabled | Step 2 |
| WebSocket connects but no messages | Event not subscribed | Step 4 |
| Bot found but doesn't respond | App not enabled in admin | Step 5 |
| Permission denied errors | Missing scope | Step 8 — add the missing scope, publish new version |
| "Python version" errors | System python is 3.8 | Use Docker, or install Python 3.11+ |
| "Module not found" errors | Dependencies not installed | Run `pip install -r requirements.txt` |
| Crash loop on startup | Missing credentials | Run `docker compose run --rm agent` (interactive setup) |
```
