# Adding Custom Tools

Add a new capability to your agent with a single decorator. The harness wraps it automatically.

## Quick start

Create a new file in `src/tools/`, e.g., `src/tools/weather.py`:

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
    # Call a weather API here
    return tool_ok({"city": city, "temp": "25°C", "condition": "Sunny"})
```

Restart the agent — the tool registers automatically and appears in the LLM's tool list.

## What the harness does for you

Every tool registered with `@register_tool` gets these automatically:

| Feature | What it does |
|---------|--------------|
| Schema validation | Checks required params and types before calling your function |
| Metrics | Counts calls and tracks success/error rate per tool |
| Tracing | Records execution in SQLite (tool name, duration, result) |
| Idempotency | Deduplicates write tool calls within the same message |

## Risk levels

The `risk_level` parameter controls confirmation behaviour when `REQUIRE_WRITE_CONFIRMATION=true`:

| Level | Behaviour |
|-------|-----------|
| `read` | Executes immediately, no confirmation |
| `write` | Asks user to confirm before executing |
| `destructive` | Asks user to confirm before executing |

## Result envelope

Always return a dict with this structure:

```python
# Success
return tool_ok({"key": "value"})

# Failure
from src.harness.result import tool_error, param_error, api_error

return param_error("city is required")         # PARAM_ERROR
return api_error("upstream returned 503")      # API_ERROR
return tool_error("CUSTOM_CODE", "detail msg") # custom error
```

The LLM sees the full result and can reason about errors to give the user a helpful response.

## Tools that call external APIs

Add API keys to `.env` and load them in your tool file:

```python
import os
MY_API_KEY = os.environ.get("MY_API_KEY", "")

@register_tool(...)
async def my_tool(query: str) -> dict:
    if not MY_API_KEY:
        from src.harness.result import auth_error
        return auth_error("MY_API_KEY not configured")
    # call the API
```

## Tools that need Feishu API access

Import the Feishu client from the lark-oapi SDK:

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

## Advanced: async vs sync functions

Both async and sync functions work:

```python
# async (preferred for I/O)
async def my_tool(query: str) -> dict:
    result = await httpx.get(...)
    return tool_ok(result.json())

# sync (fine for CPU-only work)
def my_tool(query: str) -> dict:
    return tool_ok({"computed": query.upper()})
```

## Testing your tool

```python
import asyncio
from src.tools import TOOL_DEFINITIONS  # triggers discover_tools()
from src.tools.registry import execute_tool

result = asyncio.run(execute_tool("get_weather", '{"city": "Tokyo"}'))
print(result)  # {"ok": True, "data": {"city": "Tokyo", "temp": "25°C", ...}}
```
