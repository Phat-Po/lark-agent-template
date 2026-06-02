# 安装引导 Prompt

将以下内容粘贴到任何 AI 助手（Claude、ChatGPT、Cursor 等）中，获得一步步的安装引导。AI 会问你做到哪一步了，自动跳过已完成的步骤。

---

```markdown
# Lark Agent Template — 安装引导

你正在帮我安装 **lark-agent-template**，一个带工具调用的飞书 AI 机器人开源模板。
仓库：https://github.com/Phat-Po/lark-agent-template

## 第 0 步：问我在哪里

先问我以下步骤中哪些已经完成：

1. 飞书应用已创建（有 App ID + App Secret）
2. 机器人能力已启用
3. 权限已添加
4. 事件订阅已配置（WebSocket + im.message.receive_v1）
5. 应用已发布并在管理后台启用
6. 仓库已克隆，.env 已配置
7. 机器人运行中（Docker 或 Python）
8. 机器人在飞书中能回复消息

问："你现在在第几步？（1-8，或者描述你已经做了什么）"
然后跳到那一步继续。

---

## 第 1 步：创建飞书应用

1. 打开 https://open.feishu.cn/
2. 点击 **创建应用** → **企业自建应用**
3. 填写应用名称和描述
4. 进入 **凭证与基础信息** → 复制 **App ID** 和 **App Secret**（保存好，后面 .env 要用）

## 第 2 步：启用机器人能力

1. 进入 **添加应用能力**
2. 找到 **机器人** → 点击 **启用**
3. 不启用的话，机器人不会出现在飞书搜索中

## 第 3 步：添加权限

进入 **权限管理**，启用以下所有权限：

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

这覆盖所有内置工具（日历、任务、文档、云空间、消息、搜索）。
逐个复制权限名称粘贴到飞书权限页面的搜索框中并启用。

## 第 4 步：配置事件订阅

1. 进入 **事件订阅**
2. 在 **订阅方式** 下，选择 **使用长连接接收事件（WebSocket）**
3. 点击 **添加事件** → 搜索并添加 `im.message.receive_v1`
4. 飞书会要求先启用至少一个权限：
   - **读取用户发给机器人的单聊消息**（接收私聊）
   - **获取群组中用户@机器人消息**（接收群聊 @ 提及）
5. 确认这些权限在权限管理中显示 **已开通**，然后返回完成事件添加

## 第 5 步：发布并启用

1. 进入 **版本管理与发布** → **创建版本**
2. 填写版本说明 → **提交**
3. 如果你是企业管理员，立即审批
4. 打开 https://admin.feishu.cn → **应用管理** → 找到应用 → **启用**

## 第 6 步：克隆并配置

```bash
git clone https://github.com/Phat-Po/lark-agent-template.git
cd lark-agent-template
cp .env.example .env
```

编辑 `.env` 填入：

| 变量 | 获取方式 |
|------|----------|
| `LARK_APP_ID` | 飞书应用凭证页面 |
| `LARK_APP_SECRET` | 飞书应用凭证页面 |
| `LLM_API_KEY` | 你的 LLM 提供商（OpenAI/DeepSeek/Mimo 等） |
| `LLM_BASE_URL` | 你的 LLM 提供商 API 地址 |
| `LLM_MODEL` | 模型名称（如 gpt-4o、deepseek-chat） |

可选：
| `SEARCH_API_KEY` | SerpAPI Key（只有需要网页搜索工具时才填） |

**重要**：不要跳过此步骤。没有有效的 `LARK_APP_ID` 和 `LARK_APP_SECRET`，机器人会崩溃循环。如果日志中看到 `FeishuChannel requires app_id and app_secret`，回来填写 `.env`。

## 第 7 步：运行机器人

**用 Docker（推荐）：**
```bash
docker compose up --build
```

**不用 Docker（需要 Python 3.11+）：**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
set -a && source .env && set +a
uvicorn src.main:app --host 0.0.0.0 --port 8080
```

日志中应该看到：
```
Lark Agent Template started
  Tools: 15 loaded
connected to wss://msg-frontier.feishu.cn/ws/v2 ...
```

## 第 8 步：启用所有权限

即使机器人在运行，没有正确权限工具也不会工作。进入飞书应用 → **权限管理** 启用以下所有权限：

### 消息相关（先启用）

| 权限 | 说明 |
|------|------|
| `im:message` | 接收和发送消息 |
| `im:message:send_as_bot` | 以机器人身份发送消息 |
| `im:message:readonly` | 读取消息内容 |
| `im:message.p2p_msg:readonly` | 读取私聊消息 |
| `im:message.group_at_msg:readonly` | 读取群聊 @ 提及 |

### 日历工具

| 权限 | 说明 |
|------|------|
| `calendar:calendar` | 访问日历 |
| `calendar:calendar:read` | 列出日历 |
| `calendar:calendar:readonly` | 读取日历信息 |
| `calendar:calendar.event:read` | 列出/读取事件 |
| `calendar:calendar.event:create` | 创建事件 |
| `calendar:calendar.event:delete` | 删除事件 |
| `calendar:calendar.event:update` | 更新事件 |
| `calendar:calendar.free_busy:read` | 读取忙闲状态 |

### 任务工具

| 权限 | 说明 |
|------|------|
| `task:task` | 完整任务访问 |
| `task:task:read` | 读取任务 |
| `task:task:write` | 创建/更新/删除任务 |
| `task:tasklist:read` | 读取任务列表 |
| `task:tasklist:write` | 管理任务列表 |
| `task:comment:read` | 读取任务评论 |
| `task:comment:write` | 写入任务评论 |

### 文档和云空间工具

| 权限 | 说明 |
|------|------|
| `docx:document` | 完整文档访问 |
| `docx:document:readonly` | 读取文档 |
| `docx:document:create` | 创建文档 |
| `docs:document.content:read` | 读取文档内容 |
| `drive:drive` | 完整云空间访问 |
| `drive:drive:readonly` | 列出/读取云空间文件 |
| `drive:drive.search:readonly` | 搜索文档 |
| `drive:file:readonly` | 读取文件元数据 |
| `drive:file:download` | 下载文件 |

### 启用权限后

1. 进入 **版本管理** → **创建版本** → **提交**
2. 如果你是管理员，审批版本
3. 打开 **admin.feishu.cn** → **应用管理** → 确认应用 **已启用**

不发布新版本，新权限不会生效。

---

## 第 9 步：测试机器人

在飞书搜索应用名称并发送消息。按顺序测试：

### 基础（只需基本权限）

| 发送 | 预期结果 |
|------|----------|
| `你好` | 机器人回复问候 |
| `你能做什么？` | 机器人列出能力 |

### 日历（需要日历权限）

| 发送 | 预期结果 |
|------|----------|
| `今天有什么日程？` | 机器人读取并列出今天的事件 |
| `明天下午3点创建一个会议叫"团队同步"` | 机器人创建日历事件 |

### 任务（需要任务权限）

| 发送 | 预期结果 |
|------|----------|
| `我有什么任务？` | 机器人列出待办任务 |
| `创建一个任务：买牛奶` | 机器人创建飞书任务 |

### 文档（需要文档/云空间权限）

| 发送 | 预期结果 |
|------|----------|
| `搜索文档：项目计划` | 机器人搜索文档 |
| `创建一个文档叫"会议纪要"` | 机器人创建新文档 |

### 网页搜索（需要在 .env 中设置 SEARCH_API_KEY）

| 发送 | 预期结果 |
|------|----------|
| `搜索网页：AI 新闻 2026` | 机器人返回搜索结果 |

### 如果测试失败

| 症状 | 原因 | 解决 |
|------|------|------|
| 机器人完全不回复 | 事件订阅缺失 | 第 4 步 — 添加 `im.message.receive_v1` |
| "permission denied" 或 "scope" 错误 | 缺少权限 | 回到第 8 步，添加缺失权限，发布新版本 |
| "API key not configured" | SEARCH_API_KEY 未设置 | 添加到 `.env`，重启机器人 |
| 机器人回复但工具静默失败 | 权限已启用但未发布 | 创建并发布新应用版本 |

---

## 故障排查

| 症状 | 原因 | 解决 |
|------|------|------|
| 飞书搜索不到机器人 | 未启用机器人能力 | 第 2 步 |
| WebSocket 连接但没有消息 | 未订阅事件 | 第 4 步 |
| 找到机器人但不回复 | 管理后台未启用 | 第 5 步 |
| 权限拒绝错误 | 缺少权限 | 第 8 步 — 添加权限，发布新版本 |
| "Python version" 错误 | 系统 python 是 3.8 | 用 Docker，或安装 Python 3.11+ |
| "Module not found" 错误 | 依赖未安装 | 运行 `pip install -r requirements.txt` |
| 启动时崩溃循环 | 缺少凭证 | 运行 `docker compose run --rm agent`（交互式配置） |
```
