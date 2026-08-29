"""Low-level authenticated HTTP calls to the Zoho CRM API.

Owns its own get-token / refresh-on-401 / retry-once flow instead of
inheriting a shared base class, so every Zoho HTTP concern lives
entirely in this one file; contacts/service.py and leads/service.py
just call `authenticated_request`.
"""

import httpx

from app.core.config import get_settings
from app.core.exceptions import ProviderAuthError
from app.core.http_client import request_with_retry
from app.core.time import utcnow
from app.modules.zoho.auth import service as zoho_auth
from app.modules.zoho.auth.models import ZohoToken


def base_url() -> str:
    settings = get_settings()
    return f"{settings.zoho_api_base_url}/crm/v3"


async def authenticated_request(
    method: str, url: str, **kwargs
) -> httpx.Response:
    """The Zoho-specific version of the "get/refresh a token, send,

    retry once on 401" flow that used to be a shared Template Method.
    """
    token = zoho_auth.load_token()
    if token is None:
        raise ProviderAuthError(
            "Zoho is not authorized yet. Complete the OAuth flow via "
            "GET /zoho/auth/authorize first."
        )
    if token.expires_at is None or utcnow() >= token.expires_at:
        token = await _refresh(token)

    response = await _send(method, url, token.access_token, **kwargs)

    if response.status_code == 401:
        token = await _refresh(token)
        response = await _send(method, url, token.access_token, **kwargs)
        if response.status_code == 401:
            raise ProviderAuthError(
                "zoho: authentication failed after token refresh"
            )

    return response


async def _refresh(token: ZohoToken) -> ZohoToken:
    if not token.refresh_token:
        raise ProviderAuthError(
            "No Zoho refresh_token on file; re-authorize via "
            "GET /zoho/auth/authorize."
        )
    return await zoho_auth.refresh_access_token(token.refresh_token)


async def _send(
    method: str, url: str, access_token: str, **kwargs
) -> httpx.Response:
    headers = {
        **kwargs.pop("headers", {}),
        "Authorization": f"Zoho-oauthtoken {access_token}",
    }
    return await request_with_retry(method, url, headers=headers, **kwargs)
