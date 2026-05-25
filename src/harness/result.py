"""Standard error taxonomy for tool results.

Canonical error codes (7 categories):
  PARAM_ERROR   — missing, invalid, or malformed parameters
  POLICY_ERROR  — blocked by business policy or rate guard
  AUTH_ERROR    — OAuth token missing, expired, or invalid
  API_ERROR     — upstream API returned an error
  LLM_ERROR     — LLM call failed (bad request, rate limit, auth, generic)
  TIMEOUT_ERROR — upstream call timed out
  INTERNAL_ERROR — unexpected internal failure

Workflow state (not an error category):
  CONFIRM_REQUIRED — write tool needs explicit user confirmation
"""


def tool_ok(data: dict | None = None) -> dict:
    return {"ok": True, "data": data or {}}


def tool_error(code: str, detail: str) -> dict:
    return {"ok": False, "error": {"code": code, "detail": detail}}


# --- Canonical error helpers ---


def param_error(detail: str) -> dict:
    return tool_error("PARAM_ERROR", detail)


def policy_error(detail: str) -> dict:
    return tool_error("POLICY_ERROR", detail)


def auth_error(detail: str = "OAuth token missing or expired") -> dict:
    return tool_error("AUTH_ERROR", detail)


def api_error(detail: str) -> dict:
    return tool_error("API_ERROR", detail)


def llm_error(detail: str) -> dict:
    return tool_error("LLM_ERROR", detail)


def timeout_error(detail: str = "Request timed out") -> dict:
    return tool_error("TIMEOUT_ERROR", detail)


def internal_error(detail: str) -> dict:
    return tool_error("INTERNAL_ERROR", detail)
