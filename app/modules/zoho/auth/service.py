"""Zoho OAuth 2.0: authorization-code exchange + refresh-token flow.

Owns its own ZohoToken table and refresh logic.
"""

import datetime
import logging
from urllib.parse import urlencode

from app.core.config import get_settings
from app.core.exceptions import ProviderAuthError
from app.core.http_client import request_with_retry
from app.core.time import utcnow
from app.db.session import SessionLocal
from app.modules.zoho.auth.models import ZohoToken

logger = logging.getLogger(__name__)

ZOHO_SCOPES = "ZohoCRM.modules.contacts.ALL,ZohoCRM.modules.leads.ALL"

# Refresh a little before the real expiry to avoid racing a 401.
_EXPIRY_SAFETY_MARGIN = datetime.timedelta(seconds=60)


def build_authorization_url() -> str:
    settings = get_settings()
    params = {
        "scope": ZOHO_SCOPES,
        "client_id": settings.zoho_client_id,
        "response_type": "code",
        "access_type": "offline",
        "redirect_uri": settings.zoho_redirect_uri,
        "prompt": "consent",
    }
    base = settings.zoho_accounts_base_url
    return f"{base}/oauth/v2/auth?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> ZohoToken:
    settings = get_settings()
    response = await request_with_retry(
        "POST",
        f"{settings.zoho_accounts_base_url}/oauth/v2/token",
        data={
            "grant_type": "authorization_code",
            "client_id": settings.zoho_client_id,
            "client_secret": settings.zoho_client_secret,
            "redirect_uri": settings.zoho_redirect_uri,
            "code": code,
        },
    )
    payload = response.json()
    if "access_token" not in payload:
        raise ProviderAuthError(
            "Zoho token exchange failed",
            details={"response": payload},
        )
    return _save_token(payload, require_refresh_token=True)


async def refresh_access_token(refresh_token: str) -> ZohoToken:
    settings = get_settings()
    response = await request_with_retry(
        "POST",
        f"{settings.zoho_accounts_base_url}/oauth/v2/token",
        data={
            "grant_type": "refresh_token",
            "client_id": settings.zoho_client_id,
            "client_secret": settings.zoho_client_secret,
            "refresh_token": refresh_token,
        },
    )
    payload = response.json()
    if "access_token" not in payload:
        raise ProviderAuthError(
            "Zoho token refresh failed",
            details={"response": payload},
        )
    payload.setdefault("refresh_token", refresh_token)
    return _save_token(payload, require_refresh_token=False)


def load_token() -> ZohoToken | None:
    with SessionLocal() as db:
        return db.query(ZohoToken).first()


def _save_token(payload: dict, *, require_refresh_token: bool) -> ZohoToken:
    expires_in = payload.get("expires_in", 3600)
    ttl = datetime.timedelta(seconds=expires_in)
    expires_at = utcnow() + ttl - _EXPIRY_SAFETY_MARGIN

    with SessionLocal() as db:
        token = db.query(ZohoToken).first()
        if token is None:
            token = ZohoToken(access_token="")
            db.add(token)

        token.access_token = payload["access_token"]
        refresh_token = payload.get("refresh_token")
        if refresh_token:
            token.refresh_token = refresh_token
        elif require_refresh_token and not token.refresh_token:
            raise ProviderAuthError(
                "Zoho did not return a refresh_token. Re-authorize with "
                "prompt=consent and access_type=offline."
            )
        token.expires_at = expires_at

        db.commit()
        db.refresh(token)
        logger.info("Zoho token stored, expires_at=%s", expires_at.isoformat())
        return token
