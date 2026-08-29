"""Low-level authenticated HTTP calls to the Shopify Admin API.

Standalone: owns its own token-lookup / retry flow, with nothing
shared with Zoho's client.py. Shopify's offline token doesn't
expire, and a static custom-app token doesn't refresh either, so
there's no refresh-on-401 branch here beyond re-reading whatever
token is on file - a genuinely invalid token surfaces as a plain
401/403 from Shopify.
"""

import httpx

from app.core.config import get_settings
from app.core.http_client import request_with_retry
from app.modules.shopify.auth import service as shopify_auth


def base_url() -> str:
    settings = get_settings()
    return (
        f"https://{settings.shopify_shop_domain}"
        f"/admin/api/{settings.shopify_api_version}"
    )


def _current_token() -> str:
    token = shopify_auth.load_token()
    if token is not None:
        return token.access_token
    return shopify_auth.get_static_access_token()


async def authenticated_request(
    method: str, url: str, **kwargs
) -> httpx.Response:
    headers = {
        **kwargs.pop("headers", {}),
        "X-Shopify-Access-Token": _current_token(),
    }
    return await request_with_retry(method, url, headers=headers, **kwargs)
