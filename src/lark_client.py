"""Shared Lark API client singleton."""

import lark_oapi as lark
from src.config import LARK_APP_ID, LARK_APP_SECRET

_tenant_client: lark.Client | None = None


def get_client() -> lark.Client:
    """Get tenant-authenticated client (app-level access, auto token)."""
    global _tenant_client
    if _tenant_client is None:
        _tenant_client = (
            lark.Client.builder()
            .app_id(LARK_APP_ID)
            .app_secret(LARK_APP_SECRET)
            .build()
        )
    return _tenant_client
