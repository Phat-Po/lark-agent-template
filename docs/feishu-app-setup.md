# Feishu App Setup

Complete checklist for creating and configuring a Feishu app to work with this agent.

## Checklist

- [ ] Create app, copy App ID + App Secret
- [ ] Enable Bot capability
- [ ] Add required permissions
- [ ] Set event subscription to WebSocket mode
- [ ] Add `im.message.receive_v1` event
- [ ] Publish a version
- [ ] Enable the app in admin console
- [ ] Fill `.env` with credentials

---

## 1. Create the app

1. Go to [open.feishu.cn](https://open.feishu.cn/)
2. Click **Create App** → **Enterprise Custom App**
3. Fill in app name and description
4. Go to **Credentials & Basic Info** — copy **App ID** and **App Secret**

## 2. Enable Bot capability

1. Go to **Add App Capability**
2. Find **Bot** → click **Enable**

Without this step, the bot won't appear in Feishu search.

## 3. Add permissions

Go to **Permissions & Scopes** → click **Batch Import/Export Permissions** → paste the JSON below → confirm import.

These cover ALL built-in tools (calendar, tasks, docs, drive, messaging, search):

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

After importing, all scopes will show as pending. When you proceed to the next step (event subscription), Feishu will require some scopes to be enabled first — follow the prompts.

## 4. Configure event subscription

1. Go to **Event Subscription**
2. Under **Subscription Method**, select **Use long connection to receive events (WebSocket)**
3. Click **Add Event** → search for and add `im.message.receive_v1`

When you add this event, Feishu will show a list of required permissions. You must enable **at least one** of the following for the event to work:

| Permission | Description |
|------------|-------------|
| 获取群组中用户@机器人消息 | Receive @ mentions in group chats |
| 读取用户发给机器人的单聊消息 | Receive direct messages to the bot |
| 获取群组中其他机器人和用户@当前机器人的消息 | Receive @ mentions from other bots |
| 获取群组中所有消息（敏感权限） | Receive all group messages (sensitive) |

For basic usage, enable the first two. Go to **Permissions & Scopes** and confirm they show **已开通** (Enabled), then return to Event Subscription to finish adding the event.

Without this step, the WebSocket connects but no messages are delivered.

## 5. Publish the app

1. Go to **Version Management & Publish** → **Create a version**
2. Fill in version notes → **Submit**
3. If you are the enterprise admin, approve immediately

## 6. Enable in admin console

Even after publishing, the app must be enabled for your organization:

1. Go to [admin.feishu.cn](https://admin.feishu.cn)
2. Left menu → **App Management**
3. Find your app → click **Enable**

## 7. Configure `.env`

```
LARK_APP_ID=cli_xxxxxxxxxxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 8. Test the bot

Search for your app name in Feishu and send it a message. Try these tests:

### Basic (works with just im:message scopes)

| Send | Expected |
|------|----------|
| `Hello` | Bot responds with a greeting |
| `What can you do?` | Bot lists its capabilities |

### Calendar (needs calendar:calendar.event:read + calendar:calendar)

| Send | Expected |
|------|----------|
| `What's on my calendar today?` | Bot lists today's events |
| `Create a meeting tomorrow at 3pm called "Team Sync"` | Bot creates a calendar event |

### Tasks (needs task:task:read + task:task:write)

| Send | Expected |
|------|----------|
| `What tasks do I have?` | Bot lists your open tasks |
| `Create a task: buy milk` | Bot creates a Feishu task |

### Documents (needs docx:document:readonly + drive:drive:readonly)

| Send | Expected |
|------|----------|
| `Search docs: project plan` | Bot searches your documents |
| `Create a document called "Meeting Notes"` | Bot creates a new doc |

### Web search (needs SEARCH_API_KEY in .env)

| Send | Expected |
|------|----------|
| `Search web: AI news 2026` | Bot returns web search results |

### After adding new scopes

Every time you enable new scopes, you must:
1. **Create a new version** in Version Management
2. **Submit and approve** the version
3. New scopes only take effect after the version is published

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot not found in Feishu search | Bot capability not enabled | Step 2 |
| WebSocket connects but no messages | `im.message.receive_v1` not subscribed | Step 4 |
| Bot found but doesn't respond | App not enabled in admin console | Step 6 |
| Permission denied errors | Missing scope | Step 3 — add the scope, publish new version |
| Tool returns "scope" error | Scope enabled but version not published | Create + publish a new app version |
| Crash loop on startup | Missing credentials | Run `docker compose run --rm agent` |
