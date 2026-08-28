"""ZohoCRMProvider: the auth/base-request half of the Zoho Strategy

implementation. The Contacts/Leads Adapter logic lives in sibling
modules and is mixed in below so each concern stays in its own file.
"""

import datetime

from app.core.config import get_settings
from app.core.exceptions import ProviderAuthError
from app.core.time import utcnow
from app.providers.base import BaseCRMProvider
from app.providers.zoho import auth as zoho_auth
from app.providers.zoho.contacts import ZohoContactsMixin
from app.providers.zoho.leads import ZohoLeadsMixin


class ZohoCRMProvider(ZohoContactsMixin, ZohoLeadsMixin, BaseCRMProvider):
    name = "zoho"

    def __init__(self) -> None:
        self._settings = get_settings()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: datetime.datetime | None = None

    @property
    def base_url(self) -> str:
        return f"{self._settings.zoho_api_base_url}/crm/v3"

    async def get_access_token(self) -> str:
        if self._access_token is None:
            self._load_cached_token()
        if self._access_token is None:
            raise ProviderAuthError(
                "Zoho is not authorized yet. Complete the OAuth flow via "
                "GET /zoho/auth/authorize first."
            )
        return self._access_token

    async def refresh_token(self) -> str:
        if self._refresh_token is None:
            self._load_cached_token()
        if self._refresh_token is None:
            raise ProviderAuthError(
                "No Zoho refresh_token on file; re-authorize via "
                "GET /zoho/auth/authorize."
            )
        token = await zoho_auth.refresh_access_token(self._refresh_token)
        self._apply_token(token)
        return self._access_token

    def is_token_expired(self) -> bool:
        if self._expires_at is None:
            return True
        return utcnow() >= self._expires_at

    def build_auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Zoho-oauthtoken {token}"}

    def _load_cached_token(self) -> None:
        token = zoho_auth.load_token()
        if token is not None:
            self._apply_token(token)

    def _apply_token(self, token) -> None:
        self._access_token = token.access_token
        self._refresh_token = token.refresh_token
        self._expires_at = token.expires_at
