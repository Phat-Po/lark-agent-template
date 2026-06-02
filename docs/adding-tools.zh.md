# 添加自定义工具

用一个装饰器就能给 Agent 添加新能力。Harness 会自动包装。

## 快速开始

在 `src/tools/` 下创建新文件，例如 `src/tools/weather.py`：

```python
from src.tools.registry import register_tool
from src.harness.result import tool_ok, tool_error

@register_tool(
    name="get_weather",
    description="Get current weather for a city",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
        },
        "required": ["city"],
    },
    risk_level="read",
)
async def get_weather(city: str) -> dict:
    # 在这里调用天气 API
    return tool_ok({"city": city, "temp": "25°C", "condition": "Sunny"})
```

重启 Agent —— 工具自动注册，出现在 LLM 的工具列表中。

## Harness 自动提供的能力

用 `@register_tool` 注册的每个工具自动获得：

| 能力 | 说明 |
|------|------|
| Schema 校验 | 调用前检查必填参数和类型 |
| 指标统计 | 记录调用次数、成功/错误率 |
| 追踪记录 | 写入 SQLite（工具名、耗时、结果） |
| 幂等性 | 同一消息内的写工具调用自动去重 |

## 风险等级

`risk_level` 参数控制 `REQUIRE_WRITE_CONFIRMATION=true` 时的确认行为：

| 等级 | 行为 |
|------|------|
| `read` | 立即执行，无需确认 |
| `write` | 执行前显示确认/取消卡片（DB 持久化，重启不丢失） |
| `destructive` | 执行前显示确认/取消卡片（DB 持久化，重启不丢失） |

> **注意：** 任何 `risk_level="write"` 或 `"destructive"` 的工具自动获得按钮确认流程。无需额外开发。

## 返回值格式

始终返回以下结构的 dict：

```python
# 成功
return tool_ok({"key": "value"})

# 失败
from src.harness.result import tool_error, param_error, api_error

return param_error("city is required")         # PARAM_ERROR
return api_error("upstream returned 503")      # API_ERROR
return tool_error("CUSTOM_CODE", "detail msg") # 自定义错误
```

LLM 会看到完整的结果，可以据此给用户有用的回复。

## 调用外部 API 的工具

在工具文件中加载 API Key：

```python
import os
MY_API_KEY = os.environ.get("MY_API_KEY", "")

@register_tool(...)
async def my_tool(query: str) -> dict:
    if not MY_API_KEY:
        from src.harness.result import auth_error
        return auth_error("MY_API_KEY not configured")
    # 调用 API
```

## 需要飞书 API 的工具

从 lark-oapi SDK 导入客户端：

```python
import lark_oapi as lark
from src.config import LARK_APP_ID, LARK_APP_SECRET

sdk_client = lark.Client.builder() \
    .app_id(LARK_APP_ID) \
    .app_secret(LARK_APP_SECRET) \
    .build()

@register_tool(name="get_group_members", ...)
async def get_group_members(chat_id: str) -> dict:
    request = lark.im.v1.GetChatMembersRequest.builder().chat_id(chat_id).build()
    response = await sdk_client.im.v1.chat_members.aget(request)
    if not response.success():
        return api_error(response.msg)
    return tool_ok({"members": [...]})
```

## 异步 vs 同步

两种都可以：

```python
# 异步（推荐，适合 I/O 操作）
async def my_tool(query: str) -> dict:
    result = await httpx.get(...)
    return tool_ok(result.json())

# 同步（适合纯计算）
def my_tool(query: str) -> dict:
    return tool_ok({"computed": query.upper()})
```

## 测试工具

```python
import asyncio
from src.tools import TOOL_DEFINITIONS  # 触发 discover_tools()
from src.tools.registry import execute_tool

result = asyncio.run(execute_tool("get_weather", '{"city": "Tokyo"}'))
print(result)  # {"ok": True, "data": {"city": "Tokyo", "temp": "25°C", ...}}
```
