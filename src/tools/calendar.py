"""Feishu/Lark calendar tools."""

import logging
from datetime import datetime, timedelta, timezone

from lark_oapi.api.calendar.v4 import (
    CalendarEvent,
    CalendarEventAttendee,
    CreateCalendarEventAttendeeRequest,
    CreateCalendarEventAttendeeRequestBody,
    CreateCalendarEventRequest,
    DeleteCalendarEventRequest,
    ListCalendarEventRequest,
    ListCalendarRequest,
    TimeInfo,
)

from src.lark_client import get_client
from src.logging_utils import content_hash, redact_content
from src.harness.result import api_error, auth_error, internal_error, tool_ok
from src.tools.registry import register_tool

log = logging.getLogger("lark_agent.tools.calendar")


async def _get_calendar_id() -> str | None:
    """Get the app's primary calendar ID."""
    client = get_client()
    req = ListCalendarRequest.builder().page_size(50).build()
    resp = await client.calendar.v4.calendar.alist(req)

    if not resp.success():
        log.error("Calendar list API failed: code=%s msg=%s", resp.code, resp.msg)
        return None

    if resp.data and resp.data.calendar_list:
        for cal in resp.data.calendar_list:
            if cal.type == "primary":
                return cal.calendar_id
        return resp.data.calendar_list[0].calendar_id

    return None


@register_tool(
    name="get_calendar",
    description="Get calendar events for a date range. Returns events from the Feishu calendar.",
    parameters={
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "description": "Start date YYYY-MM-DD (default: today)"},
            "end_date": {"type": "string", "description": "End date YYYY-MM-DD (default: same as start_date)"},
        },
        "required": [],
    },
    risk_level="read",
)
async def get_calendar(start_date: str = "", end_date: str = "") -> dict:
    if not start_date:
        start_date = datetime.now().strftime("%Y-%m-%d")
    if not end_date:
        end_date = start_date

    log.info("Querying calendar: %s ~ %s", start_date, end_date)

    try:
        cal_id = await _get_calendar_id()
        if not cal_id:
            return api_error("Unable to get primary calendar ID.")

        start_ts = str(int(datetime.strptime(start_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc).timestamp()))
        end_ts = str(int((datetime.strptime(end_date, "%Y-%m-%d").replace(
            tzinfo=timezone.utc) + timedelta(days=1)).timestamp()))

        req = (
            ListCalendarEventRequest.builder()
            .calendar_id(cal_id)
            .start_time(start_ts)
            .end_time(end_ts)
            .page_size(50)
            .build()
        )

        client = get_client()
        resp = await client.calendar.v4.calendar_event.alist(req)

        if not resp.success():
            log.error("Calendar event API failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        events = []
        if resp.data and resp.data.items:
            for evt in resp.data.items:
                events.append({
                    "event_id": evt.event_id,
                    "summary": evt.summary or "(no title)",
                    "start_time": _extract_time(evt.start_time),
                    "end_time": _extract_time(evt.end_time),
                    "description": evt.description or "",
                })

        return tool_ok({"events": events, "count": len(events)})

    except Exception as e:
        log.exception("get_calendar failed")
        return internal_error(str(e))


@register_tool(
    name="create_calendar_event",
    description="Create a calendar event in Feishu. start_time/end_time in ISO 8601 format.",
    parameters={
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Event title"},
            "start_time": {"type": "string", "description": "Start time, ISO 8601 format"},
            "end_time": {"type": "string", "description": "End time, ISO 8601 format"},
            "description": {"type": "string", "description": "Event description"},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of attendee open_ids",
            },
        },
        "required": ["summary", "start_time", "end_time"],
    },
    risk_level="write",
)
async def create_calendar_event(
    summary: str,
    start_time: str,
    end_time: str,
    description: str = "",
    attendees: list[str] | None = None,
) -> dict:
    log.info("Creating event: %s %s~%s attendees=%d",
             redact_content(summary), start_time, end_time,
             len(attendees) if attendees else 0)

    try:
        cal_id = await _get_calendar_id()
        if not cal_id:
            return api_error("Unable to get primary calendar ID.")

        start_ts = str(int(datetime.fromisoformat(start_time).timestamp()))
        end_ts = str(int(datetime.fromisoformat(end_time).timestamp()))

        event = (
            CalendarEvent.builder()
            .summary(summary)
            .description(description)
            .start_time(TimeInfo.builder().timestamp(start_ts).build())
            .end_time(TimeInfo.builder().timestamp(end_ts).build())
            .build()
        )

        req = (
            CreateCalendarEventRequest.builder()
            .calendar_id(cal_id)
            .request_body(event)
            .build()
        )

        client = get_client()
        resp = await client.calendar.v4.calendar_event.acreate(req)

        if not resp.success():
            log.error("Create event failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        created = resp.data.event if resp.data else None
        event_id = created.event_id if created else None

        attendee_result = None
        if attendees and event_id:
            attendee_result = await _add_attendees(client, cal_id, event_id, attendees)

        result = {
            "success": True,
            "event_id": event_id,
            "summary": summary,
        }
        if attendee_result and not attendee_result.get("ok"):
            result["attendee_warning"] = attendee_result.get("error", {})

        return tool_ok(result)

    except Exception as e:
        log.exception("create_calendar_event failed")
        return internal_error(str(e))


async def _add_attendees(client, cal_id: str, event_id: str, user_ids: list[str]) -> dict:
    try:
        attendee_list = [
            CalendarEventAttendee.builder().type("user").user_id(uid).build()
            for uid in user_ids
        ]

        body = (
            CreateCalendarEventAttendeeRequestBody.builder()
            .attendees(attendee_list)
            .need_notification(True)
            .build()
        )

        req = (
            CreateCalendarEventAttendeeRequest.builder()
            .calendar_id(cal_id)
            .event_id(event_id)
            .request_body(body)
            .build()
        )

        resp = await client.calendar.v4.calendar_event_attendee.acreate(req)

        if not resp.success():
            log.error("Add attendees failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        return tool_ok({"success": True})

    except Exception as e:
        log.exception("_add_attendees failed")
        return internal_error(str(e))


@register_tool(
    name="delete_calendar_event",
    description="Delete a calendar event from Feishu. Requires explicit user confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The event_id to delete"},
        },
        "required": ["event_id"],
    },
    risk_level="destructive",
)
async def delete_calendar_event(event_id: str) -> dict:
    log.info("Deleting event: hash=%s", content_hash(event_id))

    try:
        cal_id = await _get_calendar_id()
        if not cal_id:
            return api_error("Unable to get primary calendar ID.")

        req = (
            DeleteCalendarEventRequest.builder()
            .calendar_id(cal_id)
            .event_id(event_id)
            .need_notification("true")
            .build()
        )

        client = get_client()
        resp = await client.calendar.v4.calendar_event.adelete(req)

        if not resp.success():
            log.error("Delete event failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        return tool_ok({"success": True, "event_id": event_id})

    except Exception as e:
        log.exception("delete_calendar_event failed")
        return internal_error(str(e))


def _extract_time(time_info) -> str:
    if time_info is None:
        return ""
    if hasattr(time_info, "timestamp") and time_info.timestamp:
        ts = int(time_info.timestamp)
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if hasattr(time_info, "date") and time_info.date:
        return time_info.date
    return ""
