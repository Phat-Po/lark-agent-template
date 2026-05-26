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

Go to **Permissions & Scopes** and enable the scopes below. These cover ALL built-in tools (calendar, tasks, docs, drive, messaging, search).

### Quick list (copy-paste each name into the search box)

**Messaging (required):**
- `im:message`
- `im:message:send_as_bot`
- `im:message:readonly`
- `im:message.group_at_msg:readonly`
- `im:message.p2p_msg:readonly`
- `im:resource`
- `im:chat`
- `im:chat:read`
- `im:chat:readonly`
- `im:chat.members:read`
- `im:chat.members:write_only`

**Calendar:**
- `calendar:calendar`
- `calendar:calendar.event:create`
- `calendar:calendar.event:delete`
- `calendar:calendar.event:read`
- `calendar:calendar.event:reply`
- `calendar:calendar.event:update`
- `calendar:calendar.free_busy:read`
- `calendar:calendar:create`
- `calendar:calendar:delete`
- `calendar:calendar:read`
- `calendar:calendar:readonly`
- `calendar:calendar:subscribe`
- `calendar:calendar:update`
- `calendar:calendar.acl:create`
- `calendar:calendar.acl:delete`
- `calendar:calendar.acl:read`

**Tasks:**
- `task:task`
- `task:task:read`
- `task:task:readonly`
- `task:task:write`
- `task:task:writeonly`
- `task:tasklist:read`
- `task:tasklist:write`
- `task:comment`
- `task:comment:read`
- `task:comment:readonly`
- `task:comment:write`
- `task:custom_field:read`
- `task:custom_field:write`
- `task:section:read`
- `task:section:write`
- `task:attachment:read`
- `task:attachment:write`

**Documents & Drive:**
- `docx:document`
- `docx:document:create`
- `docx:document:readonly`
- `docx:document:write_only`
- `docs:document.content:read`
- `docs:document:copy`
- `docs:document:export`
- `docs:document:import`
- `drive:drive`
- `drive:drive:readonly`
- `drive:drive.metadata:readonly`
- `drive:drive.search:readonly`
- `drive:file`
- `drive:file:readonly`
- `drive:file:download`
- `drive:file:upload`

**Other:**
- `contact:user.base:readonly`
- `search:docs:read`

### Full JSON (for batch import or reference)

<details>
<summary>Click to expand full scope JSON</summary>

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

</details>

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

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Bot not found in Feishu search | Bot capability not enabled | Step 2 |
| WebSocket connects but no messages | `im.message.receive_v1` not subscribed | Step 4 |
| Bot found but doesn't respond | App not enabled in admin console | Step 6 |
| Permission denied errors | Missing scope | Step 3 |
