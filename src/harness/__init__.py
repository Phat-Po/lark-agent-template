"""Harness — cross-cutting infrastructure for tool execution."""

from src.harness.idempotency import (
    claim_or_skip_message,
    check_write_idempotency,
    make_write_idempotency_key,
    record_write_result,
)
from src.harness.metrics import inc, inc_tool, snapshot
from src.harness.result import (
    api_error,
    auth_error,
    internal_error,
    llm_error,
    param_error,
    policy_error,
    timeout_error,
    tool_error,
    tool_ok,
)
from src.harness.schema import validate_tool_args
from src.harness.tracing import (
    complete_run,
    fail_run,
    record_llm_call,
    record_tool_invocation,
    start_run,
)

__all__ = [
    # metrics
    "inc",
    "inc_tool",
    "snapshot",
    # result
    "tool_ok",
    "tool_error",
    "param_error",
    "policy_error",
    "auth_error",
    "api_error",
    "llm_error",
    "timeout_error",
    "internal_error",
    # schema
    "validate_tool_args",
    # tracing
    "start_run",
    "complete_run",
    "fail_run",
    "record_llm_call",
    "record_tool_invocation",
    # idempotency
    "claim_or_skip_message",
    "check_write_idempotency",
    "make_write_idempotency_key",
    "record_write_result",
]
