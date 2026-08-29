"""Shopify OAuth 2.0: authorization-code exchange for a permanent

offline access token. Owns its own ShopifyToken table.

The callback needs two checks Zoho's doesn't: an HMAC signature over
the query string (proves the redirect came from Shopify, using the
app's client secret) and a `state` nonce (defends against CSRF).
Both are enforced here before a code is ever exchanged.

Falls back to a static custom-app access token
(`get_static_access_token`) when no OAuth token has been stored yet,
so existing SHOPIFY_ACCESS_TOKEN setups keep working unchanged.
"""

import hashlib
import hmac
import logging
import re
import secrets
from urllib.parse import urlencode

from app.core.config import get_settings
from app.core.exceptions import ProviderAuthError
from app.core.http_client import request_with_retry
from app.db.session import SessionLocal
from app.modules.shopify.auth.models import ShopifyToken

logger = logging.getLogger(__name__)

_SHOP_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$")

# Pending OAuth nonces, consumed on first use. Process-local: fine
# for this single-tenant app, wouldn't survive a multi-worker
# deployment or a restart mid-flow.
_pending_states: set[str] = set()


def get_static_access_token() -> str:
    settings = get_settings()
    if not settings.shopify_access_token:
        raise ProviderAuthError(
            "Shopify is not authorized yet. Either set "
            "SHOPIFY_ACCESS_TOKEN or complete the OAuth flow via "
            "GET /shopify/auth/authorize."
        )
    return settings.shopify_access_token


def build_authorization_url() -> str:
    settings = get_settings()
    state = secrets.token_urlsafe(24)
    _pending_states.add(state)
    params = {
        "client_id": settings.shopify_client_id,
        "scope": settings.shopify_scopes,
        "redirect_uri": settings.shopify_redirect_uri,
        "state": state,
    }
    return (
        f"https://{settings.shopify_shop_domain}/admin/oauth/authorize"
        f"?{urlencode(params)}"
    )


def verify_shop_domain(shop: str) -> None:
    settings = get_settings()
    if not _SHOP_DOMAIN_RE.match(shop):
        raise ProviderAuthError(f"Invalid Shopify shop domain: {shop}")
    if shop != settings.shopify_shop_domain:
        raise ProviderAuthError(
            f"Shopify callback shop {shop!r} does not match configured "
            f"SHOPIFY_SHOP_DOMAIN {settings.shopify_shop_domain!r}"
        )


def verify_state(state: str) -> None:
    try:
        _pending_states.remove(state)
    except KeyError:
        raise ProviderAuthError(
            "Invalid or expired Shopify OAuth state"
        ) from None


def verify_callback_hmac(params: dict, received_hmac: str) -> None:
    settings = get_settings()
    message = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    digest = hmac.new(
        settings.shopify_client_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest, received_hmac):
        raise ProviderAuthError("Shopify callback HMAC verification failed")


async def handle_callback(*, params: dict, hmac_signature: str) -> None:
    shop = params.get("shop", "")
    code = params.get("code", "")
    state = params.get("state", "")

    verify_shop_domain(shop)
    verify_state(state)
    verify_callback_hmac(params, hmac_signature)
    await exchange_code_for_token(shop, code)


async def exchange_code_for_token(shop: str, code: str) -> ShopifyToken:
    settings = get_settings()
    response = await request_with_retry(
        "POST",
        f"https://{shop}/admin/oauth/access_token",
        json={
            "client_id": settings.shopify_client_id,
            "client_secret": settings.shopify_client_secret,
            "code": code,
        },
    )
    payload = response.json()
    if "access_token" not in payload:
        raise ProviderAuthError(
            "Shopify token exchange failed",
            details={"response": payload},
        )
    return _save_token(payload)


def load_token() -> ShopifyToken | None:
    with SessionLocal() as db:
        return db.query(ShopifyToken).first()


def _save_token(payload: dict) -> ShopifyToken:
    with SessionLocal() as db:
        token = db.query(ShopifyToken).first()
        if token is None:
            token = ShopifyToken(access_token="")
            db.add(token)

        token.access_token = payload["access_token"]

        db.commit()
        db.refresh(token)
        logger.info(
            "Shopify token stored, scope=%s", payload.get("scope")
        )
        return token
