"""Web search tool (SerpAPI / Google)."""

import asyncio
import logging

from src.config import SEARCH_API_KEY
from src.logging_utils import content_hash, redact_content
from src.harness.result import api_error, internal_error, timeout_error, auth_error, tool_ok
from src.tools.registry import register_tool

log = logging.getLogger("lark_agent.tools.search")
_SEARCH_TIMEOUT_SECONDS = 10


@register_tool(
    name="search_web",
    description="Search the web using SerpAPI (Google). Use for questions requiring real-time information.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keyword"},
        },
        "required": ["query"],
    },
    risk_level="read",
)
async def search_web(query: str) -> dict:
    log.info("Web search: %s hash=%s", redact_content(query), content_hash(query))

    if not SEARCH_API_KEY:
        return auth_error("SEARCH_API_KEY is not configured.")

    try:
        data = await asyncio.wait_for(
            asyncio.to_thread(_run_serpapi_search, query),
            timeout=_SEARCH_TIMEOUT_SECONDS,
        )
        organic = data.get("organic_results", [])
        return tool_ok({"results": [_format_result(r) for r in organic[:5]]})
    except asyncio.TimeoutError:
        log.warning("SerpAPI search timed out: %s", query)
        return timeout_error("Search request timed out.")
    except Exception as e:
        log.warning("SerpAPI search failed: %s", e)
        return internal_error(str(e))


def _run_serpapi_search(query: str) -> dict:
    from serpapi import GoogleSearch

    params = {
        "engine": "google",
        "q": query,
        "num": 5,
        "api_key": SEARCH_API_KEY,
    }
    return GoogleSearch(params).get_dict()


def _format_result(result: dict) -> dict:
    return {
        "title": result.get("title", ""),
        "url": result.get("link", ""),
        "snippet": result.get("snippet", ""),
    }
