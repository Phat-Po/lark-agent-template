# 架构

## 消息流

```
飞书应用
    │  WebSocket（长连接）
    ▼
FeishuChannel (lark-oapi)
    │  on_message 回调
    ▼
src/main.py — on_message()
    │  幂等性检查（跳过重复消息）
    │  追踪：start_run()
    ▼
src/agent.py — chat()
    │  加载会话历史
    │  加载持久化记忆
    │  构建系统提示词
    ▼
_run_agent_loop()
    │  POST 到 LLM API（OpenAI 兼容）
    │  ◄─── 响应中的 tool_calls ───►
    │            │
    │       execute_tool()
    │            │
    │       工具注册表
    │       (harness 包装)
    │            │
    │       飞书 API / 外部 API
    │            │
    │       结果 → 反馈给 LLM
    │  ◄─── 最多 10 轮 ──►
    │  最终文本回复
    ▼
src/main.py — _send_card_with_fallback()
    │  以 CardKit v2 卡片发送
    │  失败时回退到纯文本
    ▼
飞书应用（用户看到回复）
```

## Harness 层

每个工具调用都经过 harness 层：

```
execute_tool(name, args_json)
    │
    ├── 1. Schema 校验 (validate_tool_args)
    │       检查必填参数、类型是否符合 JSON Schema
    │
    ├── 2. 指标统计 (inc_tool)
    │       记录调用次数、跟踪成功/错误率
    │
    ├── 3. 追踪记录 (record_tool_invocation)
    │       写入 SQLite：工具名、耗时、结果码
    │
    └── 4. 执行工具函数
            返回结果信封 {ok, data, error}
```

写工具的幂等性在 `src/agent.py` 中调用 `execute_tool` 之前处理，确保重复消息不会重新执行同一个写操作。

## 交互式卡片

回复以 CardKit v2 卡片渲染（彩色标题 + Markdown），而非纯文本。

| 卡片类型 | 标题颜色 | 用途 |
|----------|----------|------|
| `build_reply_card(text)` | 蓝色（默认） | 普通回复 |
| `build_confirm_card(text, tool, action_id)` | 蓝色 | 带确认/取消按钮的写操作确认卡片 |
| `build_error_card(error_text)` | 红色 | 错误消息 |

### SDK 补丁

启动时应用两个补丁修复 lark-oapi SDK 的 bug：

1. **`_patch_ws_client_loop()`** — SDK 的 `WSClient.start()` 使用模块级 `loop` 变量，与 uvicorn 的运行中事件循环冲突。此补丁创建一个全新的、未运行的循环。
2. **`_patch_ws_client_card_handler()`** — SDK 的 `_handle_data_frame` 会静默丢弃 `MessageType.CARD` 消息。此补丁将其路由到与 EVENT 相同的事件处理器。

### 回退策略

所有卡片发送都经过 `_send_card_with_fallback()`：如果卡片发送失败（大小限制、API 错误），回退到纯文本。超过 28KB 的卡片自动截断。

## 数据库持久化确认流程

当写入/删除工具被调用时：

1. Agent 在 SQLite 中存储一个 `pending_action` 行（以 `action_id` 为键，UUID）。
2. 返回带确认/取消按钮的确认卡片给用户。
3. 用户点击按钮后，`on_card_action` 在数据库中查找 `action_id`，执行或取消。
4. 待确认操作在 30 分钟后过期（`PENDING_ACTION_TTL_SECONDS`）。过期点击会显示友好提示。
5. 每个用户可以同时有多个待确认操作——每个都有自己的 `action_id`。

此设计在机器人重启后仍然有效（数据库持久化，非内存）。

## 超时包装器

外部 API 调用（如飞书消息发送）用 `with_timeout()` 包装（默认 15 秒）。超时时返回清理过的错误消息，而非挂起。

## 数据库 Schema

```sql
conversations      -- 完整消息日志（用户 + 助手轮次）
memories           -- 每用户持久化记忆
agent_runs         -- 每条处理的消息一行（追踪）
llm_calls          -- 每次 LLM API 调用一行（延迟、token 数）
tool_invocations   -- 每次工具调用一行（耗时、结果）
pending_actions    -- 数据库持久化的确认按钮（action_id 主键，expires_at）
messages           -- 幂等性表（message_id → 状态）
idempotency_keys   -- 写工具去重（hash → 结果）
```

## 配置

所有配置通过环境变量设置。完整列表见 `.env.example`。

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LARK_APP_ID` | — | 飞书应用 ID（必填） |
| `LARK_APP_SECRET` | — | 飞书应用密钥（必填） |
| `LLM_API_KEY` | — | LLM 提供商 API Key（必填） |
| `LLM_BASE_URL` | openai | LLM API 地址 |
| `LLM_MODEL` | gpt-4o | 模型名称 |
| `BOT_DISPLAY_NAME` | Lark Agent | 卡片标题中显示的机器人名称 |
| `MAX_HISTORY_ROUNDS` | 20 | 上下文中的最大对话轮数 |
| `MAX_TOKEN_BUDGET` | 3000 | LLM 响应的最大 token 数 |
| `REQUIRE_WRITE_CONFIRMATION` | true | 写入/危险操作前是否需要用户确认 |
| `SYSTEM_PROMPT_FILE` | — | 自定义系统提示词文件路径 |
| `DB_PATH` | data/agent.db | SQLite 数据库路径 |
| `LOG_LEVEL` | INFO | 日志级别 |

## 添加 LLM 提供商

Agent 使用 OpenAI 兼容 SDK（`openai` Python 包）。切换提供商只需修改 `.env` 中的 `LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`。无需改代码。

已测试的提供商：OpenAI、DeepSeek、Mimo、Ollama（本地）。
