"""Feishu/Lark task tools."""

import logging
import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

from lark_oapi.api.task.v2 import (
    AddMembersTaskRequest,
    AddMembersTaskRequestBody,
    CreateTaskRequest,
    DeleteTaskRequest,
    Due,
    GetTaskRequest,
    InputTask,
    ListTaskRequest,
    Member,
)

from src.lark_client import get_client
from src.logging_utils import content_hash, redact_content
from src.harness.result import api_error, internal_error, param_error, tool_ok
from src.tools.registry import register_tool

log = logging.getLogger("lark_agent.tools.tasks")

_LOCAL_TZ = ZoneInfo("Asia/Shanghai")
_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


@register_tool(
    name="get_tasks",
    description="Get Feishu task list. Filter by status and optional keyword query.",
    parameters={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["all", "todo", "done"], "description": "Filter status, default todo"},
            "query": {"type": "string", "description": "Optional keyword to filter by task title or description"},
        },
        "required": [],
    },
    risk_level="read",
)
async def get_tasks(status: str = "todo", query: str = "") -> dict:
    log.info("Querying tasks: status=%s %s", status, redact_content(query) if query else "query=none")

    try:
        client = get_client()
        builder = ListTaskRequest.builder().page_size(100)

        if status == "done":
            builder = builder.completed("true")
        elif status == "todo":
            builder = builder.completed("false")

        req = builder.build()
        resp = await client.task.v2.task.alist(req)

        if not resp.success():
            log.error("Task list API failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        tasks = []
        if resp.data and resp.data.items:
            for t in resp.data.items:
                task_dict = _task_to_dict(t)
                if query and not _matches_query(task_dict, query):
                    continue
                tasks.append(task_dict)

        return tool_ok({"tasks": tasks, "count": len(tasks)})

    except Exception as e:
        log.exception("get_tasks failed")
        return internal_error(str(e))


@register_tool(
    name="get_task",
    description="Get a single Feishu task by its GUID (UUID format).",
    parameters={
        "type": "object",
        "properties": {
            "task_guid": {"type": "string", "description": "Task GUID (UUID format)"},
        },
        "required": ["task_guid"],
    },
    risk_level="read",
)
async def get_task(task_guid: str) -> dict:
    log.info("Reading task: %s", task_guid)

    if not _is_valid_task_guid(task_guid):
        return param_error("task_guid must be a UUID.")

    try:
        client = get_client()
        req = GetTaskRequest.builder().task_guid(task_guid).build()
        resp = await client.task.v2.task.aget(req)

        if not resp.success():
            log.error("Get task failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        task = resp.data.task if resp.data else None
        if not task:
            return api_error("Task not found.")

        return tool_ok({"task": _task_to_dict(task)})

    except Exception as e:
        log.exception("get_task failed")
        return internal_error(str(e))


@register_tool(
    name="create_task",
    description="Create a Feishu task. due_date format YYYY-MM-DD or ISO 8601; due_time optional HH:MM.",
    parameters={
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "Task title"},
            "due_date": {"type": "string", "description": "Due date YYYY-MM-DD or ISO 8601"},
            "due_time": {"type": "string", "description": "Optional due time HH:MM"},
            "description": {"type": "string", "description": "Task description"},
            "member_open_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of member open_ids to add as assignees",
            },
        },
        "required": ["summary"],
    },
    risk_level="write",
)
async def create_task(
    summary: str,
    due_date: str = "",
    due_time: str = "",
    description: str = "",
    member_open_ids: list[str] | None = None,
) -> dict:
    log.info("Creating task: %s due=%s time=%s members=%d",
             redact_content(summary), due_date, due_time,
             len(member_open_ids) if member_open_ids else 0)

    try:
        client = get_client()
        builder = InputTask.builder().summary(summary)

        if description:
            builder = builder.description(description)

        parsed_due = _parse_due(due_date, due_time)
        if parsed_due:
            due_dt, is_all_day = parsed_due
            due_ts = str(int(due_dt.timestamp() * 1000))
            due = Due.builder().timestamp(due_ts).is_all_day(is_all_day).build()
            builder = builder.due(due)

        task_body = builder.build()
        req = CreateTaskRequest.builder().request_body(task_body).build()
        resp = await client.task.v2.task.acreate(req)

        if not resp.success():
            log.error("Create task failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        task = resp.data.task if resp.data else None
        task_guid = getattr(task, "guid", None) if task else None

        member_result = None
        if member_open_ids and task_guid:
            member_result = await _add_task_members(client, task_guid, member_open_ids)

        result = {
            "success": True,
            "guid": task_guid,
            "task_id": getattr(task, "task_id", None) if task else None,
            "url": getattr(task, "url", "") if task else "",
            "summary": summary,
            "due": _format_due(due_dt) if parsed_due else "",
        }
        if member_result and not member_result.get("ok"):
            result["member_warning"] = member_result.get("error", {})

        return tool_ok(result)

    except Exception as e:
        log.exception("create_task failed")
        return internal_error(str(e))


async def _add_task_members(client, task_guid: str, user_ids: list[str]) -> dict:
    try:
        members = [
            Member.builder().id(uid).type("user").role("assignee").build()
            for uid in user_ids
        ]
        body = AddMembersTaskRequestBody.builder().members(members).build()
        req = AddMembersTaskRequest.builder().task_guid(task_guid).request_body(body).build()
        resp = await client.task.v2.task.aadd_members(req)

        if not resp.success():
            log.error("Add task members failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        return tool_ok({"success": True})

    except Exception as e:
        log.exception("_add_task_members failed")
        return internal_error(str(e))


@register_tool(
    name="delete_task",
    description="Delete a Feishu task by GUID. Requires explicit user confirmation.",
    parameters={
        "type": "object",
        "properties": {
            "task_guid": {"type": "string", "description": "Task GUID (UUID format)"},
        },
        "required": ["task_guid"],
    },
    risk_level="destructive",
)
async def delete_task(task_guid: str) -> dict:
    log.info("Deleting task: %s", task_guid)

    if not _is_valid_task_guid(task_guid):
        return param_error("task_guid must be a UUID.")

    try:
        client = get_client()
        req = DeleteTaskRequest.builder().task_guid(task_guid).build()
        resp = await client.task.v2.task.adelete(req)

        if not resp.success():
            log.error("Delete task failed: code=%s msg=%s", resp.code, resp.msg)
            return api_error(f"{resp.msg} (code={resp.code})")

        return tool_ok({"success": True, "task_guid": task_guid})

    except Exception as e:
        log.exception("delete_task failed")
        return internal_error(str(e))


def _extract_due(due) -> str:
    if due is None:
        return ""
    if hasattr(due, "timestamp") and due.timestamp:
        ts = int(due.timestamp)
        if ts > 10_000_000_000:
            ts = ts / 1000
        return datetime.fromtimestamp(ts, tz=_LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
    return ""


def _task_to_dict(task) -> dict:
    return {
        "guid": getattr(task, "guid", "") or "",
        "task_id": getattr(task, "task_id", "") or "",
        "summary": getattr(task, "summary", "") or "",
        "description": getattr(task, "description", "") or "",
        "status": "done" if getattr(task, "completed_at", None) else "todo",
        "due": _extract_due(getattr(task, "due", None)),
        "url": getattr(task, "url", "") or "",
    }


def _matches_query(task: dict, query: str) -> bool:
    haystack = "\n".join(
        str(task.get(k, ""))
        for k in ("summary", "description", "task_id", "guid", "url")
    ).lower()
    return query.lower() in haystack


def _is_valid_task_guid(task_guid: str) -> bool:
    return bool(task_guid and _UUID_RE.match(task_guid))


def _parse_due(due_date: str, due_time: str = "") -> tuple[datetime, bool] | None:
    if not due_date:
        return None

    text = due_date.strip()
    due_time = (due_time or "").strip()

    if "T" in text:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_LOCAL_TZ)
        return dt.astimezone(_LOCAL_TZ), False

    date_part = datetime.strptime(text, "%Y-%m-%d").date()
    if due_time:
        time_part = time.fromisoformat(due_time)
        return datetime.combine(date_part, time_part, tzinfo=_LOCAL_TZ), False

    return datetime.combine(date_part, time.min, tzinfo=_LOCAL_TZ), True


def _format_due(dt: datetime) -> str:
    return dt.astimezone(_LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
