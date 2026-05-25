# Feishu App Setup

Create a Feishu (Lark) app and configure it to work with this agent.

## 1. Create an app

1. Go to [Feishu Open Platform](https://open.feishu.cn/)
2. Click **Create App** → **Enterprise Custom App**
3. Fill in the app name and description
4. Note down **App ID** and **App Secret** from the Credentials tab

## 2. Enable required permissions

Go to **Permissions & Scopes** and add the following scopes. Enable the scopes that correspond to the tools you want to use.

### Always required (messaging)

| Scope | Description |
|-------|-------------|
| `im:message` | Receive messages |
| `im:message:send_as_bot` | Send messages as bot |
| `im:message.group_at_msg:readonly` | Read group @ messages |

### Calendar tool

| Scope | Description |
|-------|-------------|
| `calendar:calendar` | Read/write calendars |
| `calendar:calendar:readonly` | Read calendars (if write not needed) |

### Docs tool

| Scope | Description |
|-------|-------------|
| `docs:doc` | Read/write documents |
| `docs:doc:readonly` | Read documents (if write not needed) |
| `drive:drive` | Access Drive (for file management) |

### Tasks tool

| Scope | Description |
|-------|-------------|
| `task:task` | Read/write tasks |
| `task:task:readonly` | Read tasks (if write not needed) |

## 3. Enable WebSocket mode

1. Go to **Event Subscription**
2. Under **Subscription Method**, select **Use long connection to receive events (WebSocket)**
3. Enable the following events:
   - `im.message.receive_v1` — receive messages

## 4. Subscribe to message events

In **Event Subscription**, click **Add Event** and add:

- `im.message.receive_v1`

## 5. Publish the app

1. Go to **Version Management & Publish** → **Create a version**
2. Submit for review (or self-review for enterprise admin)
3. Publish the version

## 6. Add the bot to a conversation

- For **personal messages**: search for your app name in Feishu and send it a message
- For **group chats**: add the bot as a member of the group

## 7. Configure `.env`

Copy the App ID and App Secret into your `.env` file:

```
LARK_APP_ID=cli_xxxxxxxxxxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Troubleshooting

**Bot doesn't respond**: Check that `im.message.receive_v1` is subscribed and the app is published.

**Permission denied errors**: Verify the relevant scopes are enabled and the app version is published.

**WebSocket not connecting**: Ensure you selected "long connection" mode in Event Subscription, not webhook URL mode.
