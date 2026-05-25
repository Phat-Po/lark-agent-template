"""Example: Custom tool that syncs Google Calendar events to Feishu.

This file demonstrates how to build a custom tool that:
1. Calls an external API (Google Calendar)
2. Creates events in Feishu via the calendar tool
3. Handles errors properly with result envelopes

To use this example:
1. Copy this file to src/tools/google_calendar_sync.py
2. Set GOOGLE_CALENDAR_API_KEY in your .env
3. Restart the agent — the tool auto-registers

The harness wraps the tool automatically with:
- Schema validation (checks required params before calling your function)
- Metrics (counts calls and latency)
- Tracing (writes to SQLite for observability)
- Idempotency (deduplicates write tool calls within the same message)
"""

import os
import httpx

from src.tools.registry import register_tool
from src.harness.result import tool_ok, api_error, auth_error, param_error

GOOGLE_CALENDAR_API_KEY = os.environ.get("GOOGLE_CALENDAR_API_KEY", "")
GOOGLE_CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")


@register_tool(
    name="sync_google_calendar",
    description=(
        "Fetch upcoming events from Google Calendar and return them as a structured list. "
        "Use this when the user asks about their schedule from Google Calendar."
    ),
    parameters={
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of events to return (default: 10, max: 50)",
            },
            "time_min": {
                "type": "string",
                "description": "Start time in ISO 8601 format, e.g. '2024-01-01T00:00:00Z'. Defaults to now.",
            },
        },
        "required": [],
    },
    risk_level="read",
)
async def sync_google_calendar(
    max_results: int = 10,
    time_min: str = "",
) -> dict:
    """Fetch events from Google Calendar."""
    if not GOOGLE_CALENDAR_API_KEY:
        return auth_error("GOOGLE_CALENDAR_API_KEY not configured — add it to .env")

    if max_results < 1 or max_results > 50:
        return param_error("max_results must be between 1 and 50")

    params = {
        "key": GOOGLE_CALENDAR_API_KEY,
        "maxResults": max_results,
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    if time_min:
        params["timeMin"] = time_min

    url = f"https://www.googleapis.com/calendar/v3/calendars/{GOOGLE_CALENDAR_ID}/events"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
    except httpx.TimeoutException:
        from src.harness.result import timeout_error
        return timeout_error("Google Calendar API timed out")
    except Exception as exc:
        return api_error(f"Request failed: {exc}")

    if response.status_code == 401:
        return auth_error("Google Calendar API key is invalid or expired")
    if response.status_code != 200:
        return api_error(f"Google Calendar API returned {response.status_code}: {response.text[:200]}")

    data = response.json()
    events = data.get("items", [])

    formatted = []
    for event in events:
        start = event.get("start", {})
        formatted.append({
            "summary": event.get("summary", "(No title)"),
            "start": start.get("dateTime") or start.get("date", ""),
            "description": event.get("description", ""),
            "location": event.get("location", ""),
        })

    return tool_ok({
        "events": formatted,
        "count": len(formatted),
        "calendar_id": GOOGLE_CALENDAR_ID,
    })
