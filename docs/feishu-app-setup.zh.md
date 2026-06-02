# 飞书应用配置

创建和配置飞书应用的完整清单。

## 清单

- [ ] 创建应用，复制 App ID + App Secret
- [ ] 启用机器人能力
- [ ] 添加所需权限
- [ ] 设置事件订阅为 WebSocket 模式
- [ ] 添加 `im.message.receive_v1` 事件
- [ ] 发布版本
- [ ] 在管理后台启用应用
- [ ] 在 `.env` 中填入凭证

---

## 1. 创建应用

1. 打开 [open.feishu.cn](https://open.feishu.cn/)
2. 点击 **创建应用** → **企业自建应用**
3. 填写应用名称和描述
4. 进入 **凭证与基础信息** — 复制 **App ID** 和 **App Secret**

## 2. 启用机器人能力

1. 进入 **添加应用能力**
2. 找到 **机器人** → 点击 **启用**

不执行此步骤，机器人不会出现在飞书搜索中。

## 3. 添加权限

进入 **权限管理** → 点击 **批量导入/导出权限** → 粘贴以下 JSON → 确认导入。

这些覆盖所有内置工具（日历、任务、文档、云空间、消息、搜索）：

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

导入后，所有权限会显示为待启用状态。继续下一步（事件订阅）时，飞书会自动要求你先启用部分权限，按提示操作即可。

## 4. 配置事件订阅

1. 进入 **事件订阅**
2. 在 **订阅方式** 下，选择 **使用长连接接收事件（WebSocket）**
3. 点击 **添加事件** → 搜索并添加 `im.message.receive_v1`

添加此事件时，飞书会显示所需权限列表。必须至少启用以下权限之一：

| 权限 | 说明 |
|------|------|
| 获取群组中用户@机器人消息 | 接收群聊中的 @ 提及 |
| 读取用户发给机器人的单聊消息 | 接收私聊消息 |
| 获取群组中其他机器人和用户@当前机器人的消息 | 接收其他机器人的 @ 提及 |
| 获取群组中所有消息（敏感权限） | 接收所有群消息 |

基础使用建议启用前两个。进入 **权限管理** 确认显示 **已开通**，然后返回事件订阅完成添加。

不执行此步骤，WebSocket 会连接但不会收到消息。

## 5. 发布应用

1. 进入 **版本管理与发布** → **创建版本**
2. 填写版本说明 → **提交**
3. 如果你是企业管理员，立即审批

## 6. 在管理后台启用

发布后，还需要为组织启用应用：

1. 打开 [admin.feishu.cn](https://admin.feishu.cn)
2. 左侧菜单 → **应用管理**
3. 找到应用 → 点击 **启用**

## 7. 配置 `.env`

```
LARK_APP_ID=cli_xxxxxxxxxxxxxxxx
LARK_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 8. 测试机器人

在飞书搜索应用名称并发送消息。尝试以下测试：

### 基础（只需 im:message 权限）

| 发送 | 预期结果 |
|------|----------|
| `你好` | 机器人回复问候 |
| `你能做什么？` | 机器人列出能力 |

### 日历（需要 calendar:calendar.event:read + calendar:calendar）

| 发送 | 预期结果 |
|------|----------|
| `今天有什么日程？` | 机器人列出今天的事件 |
| `明天下午3点创建一个会议叫"团队同步"` | 机器人创建日历事件 |

### 任务（需要 task:task:read + task:task:write）

| 发送 | 预期结果 |
|------|----------|
| `我有什么任务？` | 机器人列出待办任务 |
| `创建一个任务：买牛奶` | 机器人创建飞书任务 |

### 文档（需要 docx:document:readonly + drive:drive:readonly）

| 发送 | 预期结果 |
|------|----------|
| `搜索文档：项目计划` | 机器人搜索文档 |
| `创建一个文档叫"会议纪要"` | 机器人创建新文档 |

### 网页搜索（需要在 .env 中设置 SEARCH_API_KEY）

| 发送 | 预期结果 |
|------|----------|
| `搜索网页：AI 新闻 2026` | 机器人返回搜索结果 |

### 添加新权限后

每次启用新权限后，必须：
1. 在版本管理中 **创建新版本**
2. **提交并审批** 版本
3. 新权限只有在版本发布后才生效

---

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| 飞书搜索不到机器人 | 未启用机器人能力 | 步骤 2 |
| WebSocket 连接但没有消息 | 未订阅 `im.message.receive_v1` | 步骤 4 |
| 找到机器人但不回复 | 管理后台未启用 | 步骤 6 |
| 权限拒绝错误 | 缺少权限 | 步骤 3 — 添加权限，发布新版本 |
| 工具返回 "scope" 错误 | 权限已启用但版本未发布 | 创建并发布新应用版本 |
| 启动时崩溃循环 | 缺少凭证 | 运行 `docker compose run --rm agent` |
