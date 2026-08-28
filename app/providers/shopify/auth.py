"""Shopify auth is a static Admin API access token (custom app),

not an OAuth flow - there's no expiry/refresh cycle to manage. This
module exists so the auth concern still lives in its own file,
mirroring the Zoho package shape, and so a future move to public-app
OAuth only touches this file.
"""

from app.core.config import get_settings
from app.core.exceptions import ProviderAuthError


def get_static_access_token() -> str:
    settings = get_settings()
    if not settings.shopify_access_token:
        raise ProviderAuthError(
            "SHOPIFY_ACCESS_TOKEN is not configured."
        )
    return settings.shopify_access_token
