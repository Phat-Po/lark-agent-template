"""Agent loop: receive a user message, call LLM, execute tools, return reply."""

import json
import os
import re
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import AsyncOpenAI, AuthenticationError, BadRequestError, RateLimitError

from src.config import (
    LLM_API_KEY,
    LLM_MODEL,
    LLM_BASE_URL,
    MAX_HISTORY_ROUNDS,
    MAX_HISTORY_TOKENS,
    MAX_TOKEN_BUDGET,
    REQUIRE_WRITE_CONFIRMATION,
    SYSTEM_PROMPT_FILE,
)
from src.harness import metrics
from src.harness.tracing import record_llm_call
from src.harness.result import param_error, policy_error, tool_error
from src.harness.idempotency import check_write_idempotency, record_write_result
from src.db import get_conn, load_pending_action
from src.memory.session import get_session_history, append_session_message
from src.memory.persistent import get_relevant_memories
from src.tools import TOOL_DEFINITIONS
from src.tools.registry import execute_tool, get_write_tool_names
from src.action_policy import (
    PolicyError,
    store_pending_action,
    take_pending_action,
    take_pending_action_by_id,
    clear_pending_action,
    get_pending_action_id,
    canonicalize_arguments,
)
from src.card_builder import build_confirm_card

log = logging.getLogger("lark_agent.agent")

client = AsyncOpenAI(
    api_key=LLM_API_KEY or "missing",
    base_url=LLM_BASE_URL,
    default_headers={"api-key": LLM_API_KEY} if LLM_API_KEY else None,
)

# Matches malformed tool calls some LLMs emit as plain text: <function=name>{...}</function>
MALFORMED_TOOL_CALL_RE = re.compile(
    r"^\s*<function=(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)>\s*(?P<args>\{.*\})\s*</function>\s*$",
    re.DOTALL,
)

# Short affirmative replies in English and Chinese that signal user confirmation
CONFIRM_RE = re.compile(
    r"^\s*(yes|ok|confirm|sure|yep|确认|好|好的|可以|行|是的|是)\s*[.!！。]?\s*$",
    re.IGNORECASE,
)

_DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful AI assistant integrated with Feishu/Lark.\n"
    "You can help users with calendar management, document operations,\n"
    "task tracking, messaging, and web search.\n"
    "Answer in the user's language. Be concise and helpful.\n"
    "You may use Feishu-flavored markdown (lark_md): bold, lists, and links\n"
    "render nicely in interactive cards.\n"
    "Current time: {current_time}"
)


def _load_system_prompt() -> str:
    if SYSTEM_PROMPT_FILE and os.path.isfile(SYSTEM_PROMPT_FILE):
        with open(SYSTEM_PROMPT_FILE) as fh:
            return fh.read().strip()
    return _DEFAULT_SYSTEM_PROMPT


# ---


async def chat(
    user_message: str,
    chat_id: str,
    sender_open_id: str = "",
    trace_id: str = "",
    msg=None,
) -> str | dict:
    """Process a user message and return the agent's reply.

    Returns a plain string for normal replies, or a dict like
    {"type": "card", "card": ...} when a confirm card should be sent.
    """
    message_id = getattr(msg, "message_id", "") if msg else ""

    history = get_session_history(chat_id, MAX_HISTORY_ROUNDS, MAX_HISTORY_TOKENS)
    memories = get_relevant_memories(sender_open_id, user_message)

    tz = ZoneInfo("UTC")
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M UTC")
    system = _load_system_prompt().format(current_time=current_time)
    if memories:
        system += "\n\nKnown context about the user:\n" + "\n".join(f"- {m}" for m in memories)

    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    append_session_message(chat_id, "user", user_message)
    save_conversation(chat_id, "user", user_message)

    if REQUIRE_WRITE_CONFIRMATION and _is_confirmation(user_message):
        pending_row = load_pending_action(chat_id, sender_open_id)
        if pending_row:
            result = await execute_tool(
                pending_row["tool_name"],
                pending_row["arguments_json"],
                trace_id=trace_id,
                message_id=message_id,
            )
            reply = _format_tool_result(pending_row["tool_name"], result)
        else:
            reply = "No pending action to confirm. Please describe what you'd like to do."
    else:
        reply = await _run_agent_loop(
            messages,
            trace_id=trace_id,
            chat_id=chat_id,
            sender_open_id=sender_open_id,
            message_id=message_id,
        )

    # Check if a pending action was stored during this turn → emit confirm card
    pending_row = load_pending_action(chat_id, sender_open_id)
    if pending_row:
        action_id = pending_row["action_id"] or get_pending_action_id(chat_id, sender_open_id)
        tool_name = pending_row["tool_name"]
        confirm_text = _build_confirm_text(tool_name, pending_row["arguments_json"])
        card_text = confirm_text if not reply else f"{reply}\n\n{confirm_text}"
        confirm_card = build_confirm_card(
            text=card_text,
            tool_name=tool_name,
            action_id=action_id,
        )
        append_session_message(chat_id, "assistant", reply)
        save_conversation(chat_id, "assistant", reply)
        return {"type": "card", "card": confirm_card}

    reply = sanitize_reply(reply)
    append_session_message(chat_id, "assistant", reply)
    save_conversation(chat_id, "assistant", reply)

    return reply


def _is_confirmation(text: str) -> bool:
    return bool(CONFIRM_RE.match(text or ""))


def save_conversation(chat_id: str, role: str, content: str) -> None:
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO conversations (chat_id, role, content) VALUES (?, ?, ?)",
            (chat_id, role, content),
        )
        conn.commit()
    except Exception:
        log.warning("save_conversation_failed", exc_info=True)


def _serialize_assistant_msg(msg) -> dict:
    d: dict = {"role": "assistant"}
    if msg.content:
        d["content"] = msg.content
    if msg.tool_calls:
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ]
    rc = getattr(msg, "reasoning_content", None)
    if rc:
        d["reasoning_content"] = rc
    return d


def _try_parse_malformed_tool_call(content: str) -> tuple[str, str] | None:
    """Parse plain-text function-call fallback some LLMs emit."""
    match = MALFORMED_TOOL_CALL_RE.match(content or "")
    if not match:
        return None
    name = match.group("name")
    args_json = match.group("args")
    try:
        json.loads(args_json)
    except json.JSONDecodeError:
        log.warning("malformed_tool_call_invalid_json: %s", content[:200])
        return None
    return name, args_json


def _synthetic_tool_call_msg(name: str, args_json: str, call_id: str) -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": args_json},
            }
        ],
    }


async def _create_completion(messages: list, *, with_tools: bool = True, trace_id: str = ""):
    import time
    kwargs: dict = {
        "model": LLM_MODEL,
        "messages": messages,
        "max_completion_tokens": MAX_TOKEN_BUDGET,
    }
    if with_tools:
        kwargs["tools"] = TOOL_DEFINITIONS
        kwargs["tool_choice"] = "auto"

    start = time.monotonic()
    try:
        resp = await client.chat.completions.create(**kwargs)
    except Exception:
        metrics.inc("llm_failures")
        raise
    finally:
        latency_ms = (time.monotonic() - start) * 1000

    metrics.inc("llm_calls")

    usage = getattr(resp, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", 0) or 0

    finish_reason = ""
    if resp.choices:
        finish_reason = getattr(resp.choices[0], "finish_reason", "") or ""

    record_llm_call(
        trace_id=trace_id,
        model=LLM_MODEL,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )

    log.info(
        "llm_call_completed",
        extra={
            "event": "llm_call_completed",
            "trace_id": trace_id,
            "model": LLM_MODEL,
            "latency_ms": round(latency_ms, 1),
            "finish_reason": finish_reason,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        },
    )
    return resp


def _format_tool_error(result: dict) -> str:
    error = result.get("error") or {}
    code = error.get("code", "INTERNAL_ERROR")
    detail = error.get("detail", "")
    if code in ("AUTH_ERROR", "TOKEN_MISSING", "TOKEN_EXPIRED"):
        return "This tool is missing authorization. Please check your API credentials."
    if code in ("PARAM_ERROR", "PARAM_MISSING", "PARAM_INVALID", "PARAM_JSON_INVALID"):
        return f"Missing or invalid parameter: {detail}".strip()
    if code == "CONFIRM_REQUIRED":
        return f"Please confirm this action: {detail}".strip()
    if code in ("POLICY_ERROR", "POLICY_REJECTED"):
        return f"Action blocked by policy: {detail}".strip()
    if code in ("FEISHU_API_ERROR", "API_ERROR"):
        return f"API error: {detail}".strip()
    if code == "TIMEOUT_ERROR":
        return "The operation timed out. Please try again."
    if code == "LLM_ERROR":
        return "LLM call failed. Please try again."
    return f"Tool failed: {detail or code}"


def _format_tool_result(tool_name: str, result: dict) -> str:
    if not result:
        return ""
    if not result.get("ok"):
        return _format_tool_error(result)
    data = result.get("data") or {}
    if tool_name == "search_web":
        results = data.get("results") or []
        if not results:
            return "Web search returned no results."
        lines = ["Here are the search results:"]
        for i, item in enumerate(results[:5], 1):
            title = item.get("title") or "Untitled"
            url = item.get("url") or ""
            snippet = item.get("snippet") or ""
            line = f"{i}. {title}"
            if snippet:
                line += f"\n{snippet}"
            if url:
                line += f"\n{url}"
            lines.append(line)
        return "\n\n".join(lines)
    return "Done."


async def _run_agent_loop(
    messages: list,
    trace_id: str = "",
    chat_id: str = "",
    sender_open_id: str = "",
    message_id: str = "",
) -> str:
    """Tool-use loop: call model → execute tools → continue until text reply."""
    latest_tool_name = ""
    latest_tool_result: dict = {}

    for iteration in range(10):
        try:
            resp = await _create_completion(messages, with_tools=True, trace_id=trace_id)
        except BadRequestError as e:
            metrics.inc("llm_errors")
            has_tool_history = any(
                m.get("role") == "tool" or m.get("tool_calls") for m in messages
            )
            if has_tool_history:
                log.error("llm_bad_request_with_tool_history: %s", e,
                          extra={"event": "llm_bad_request_with_tool_history", "trace_id": trace_id})
                return "The model returned a bad request error (tool history format issue). Please try again."
            log.warning("llm_bad_request_retry_without_tools: %s", e,
                        extra={"event": "llm_bad_request_retry_without_tools", "trace_id": trace_id})
            try:
                resp = await _create_completion(messages, with_tools=False, trace_id=trace_id)
            except BadRequestError:
                log.exception("llm_retry_without_tools_failed",
                              extra={"event": "llm_retry_without_tools_failed", "trace_id": trace_id})
                return "The model returned a bad request error. Please try rephrasing your message."
        except RateLimitError as e:
            metrics.inc("llm_errors")
            log.warning("llm_rate_limited: %s", e,
                        extra={"event": "llm_rate_limited", "trace_id": trace_id})
            return "Rate limit reached. Please try again in a moment."
        except AuthenticationError:
            metrics.inc("llm_errors")
            log.exception("llm_authentication_failed",
                          extra={"event": "llm_authentication_failed", "trace_id": trace_id})
            return "LLM API authentication failed. Please check your LLM_API_KEY."

        msg = resp.choices[0].message

        if not msg.tool_calls:
            parsed = _try_parse_malformed_tool_call(msg.content or "")
            if parsed:
                name, args_json = parsed
                result = await _execute_tool_with_guards(
                    name, args_json, trace_id, message_id, chat_id, sender_open_id
                )
                latest_tool_name = name
                latest_tool_result = result
                call_id = f"call_malformed_{iteration}"
                messages.append(_synthetic_tool_call_msg(name, args_json, call_id))
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result, ensure_ascii=False),
                })
                continue

            if not (msg.content or "").strip() and latest_tool_result:
                return _format_tool_result(latest_tool_name, latest_tool_result)
            return msg.content or ""

        messages.append(_serialize_assistant_msg(msg))

        for tc in msg.tool_calls:
            name = tc.function.name
            result = await _execute_tool_with_guards(
                name, tc.function.arguments, trace_id, message_id, chat_id, sender_open_id
            )
            latest_tool_name = name
            latest_tool_result = result
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    return "(Maximum tool rounds reached — please simplify your request.)"


async def _execute_tool_with_guards(
    name: str,
    arguments_json: str,
    trace_id: str,
    message_id: str,
    chat_id: str,
    sender_open_id: str,
) -> dict:
    """Execute a tool, applying confirmation guard and idempotency."""
    write_tools = get_write_tool_names()

    if REQUIRE_WRITE_CONFIRMATION and name in write_tools:
        try:
            args = json.loads(arguments_json)
        except json.JSONDecodeError as exc:
            return param_error(f"Invalid JSON arguments: {exc}")
        canonical = canonicalize_arguments(arguments_json)
        store_pending_action(
            chat_id, sender_open_id, name, canonical,
            request_text=f"{name}({', '.join(f'{k}={v!r}' for k, v in args.items())})",
        )
        params = ", ".join(f"{k}={v!r}" for k, v in args.items())
        return tool_error(
            "CONFIRM_REQUIRED",
            f"Ready to call {name}({params}). Reply 'confirm' to proceed.",
        )

    should_execute, cached = check_write_idempotency(message_id, name, arguments_json)
    if not should_execute:
        return cached

    result = await execute_tool(name, arguments_json, trace_id=trace_id, message_id=message_id)
    record_write_result(message_id, name, arguments_json, result)
    return result


async def execute_pending_action(pending_action, trace_id: str = "", user_id: str = "") -> str:
    """Execute a confirmed pending action (single tool)."""
    result = await execute_tool(
        pending_action.tool_name,
        pending_action.arguments_json,
        trace_id=trace_id,
    )
    return sanitize_reply(_format_tool_result(pending_action.tool_name, result))


def _expired_request_message(action) -> str:
    """User-facing message when a confirmation has expired."""
    request = (getattr(action, "request_text", "") or "").strip() if action else ""
    if request:
        return f"Your request has expired. Please re-submit: [{request}]"
    return "The pending action has expired. Please describe what you'd like to do again."


def _build_confirm_text(tool_name: str, arguments_json: str) -> str:
    """Build a generic preview of the tool call for the confirm card."""
    try:
        args = json.loads(arguments_json)
    except (json.JSONDecodeError, TypeError):
        args = {}
    lines = [f"**Confirm action: `{tool_name}`**", ""]
    for k, v in args.items():
        sval = str(v)
        if len(sval) > 120:
            sval = sval[:120] + "…"
        lines.append(f"- **{k}**: {sval}")
    lines.append("")
    lines.append("Click 确认 to proceed, 取消 to cancel.")
    return "\n".join(lines)


def sanitize_reply(text: str) -> str:
    """Normalize model output for Feishu card lark_md format."""
    text = text or ""
    text = text.strip()
    return text or "The model returned no content. Please try again."
