"""Timeout wrapper for external API calls."""

import asyncio

FEISHU_API_TIMEOUT_SECONDS = 15


async def with_timeout(coro, timeout: float = FEISHU_API_TIMEOUT_SECONDS):
    """Wrap an awaitable with a timeout. Raises asyncio.TimeoutError on expiry."""
    return await asyncio.wait_for(coro, timeout=timeout)
