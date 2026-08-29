import hashlib
import hmac

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import ProviderAuthError
from app.modules.shopify.auth import service as shopify_auth


def _sign(params: dict) -> str:
    settings = get_settings()
    message = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hmac.new(
        settings.shopify_client_secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def test_build_authorization_url_includes_client_id_and_shop():
    settings = get_settings()
    url = shopify_auth.build_authorization_url()

    assert settings.shopify_client_id in url
    assert settings.shopify_shop_domain in url
    assert "state=" in url


def test_verify_shop_domain_rejects_mismatch():
    with pytest.raises(ProviderAuthError):
        shopify_auth.verify_shop_domain("someone-elses-shop.myshopify.com")


def test_verify_shop_domain_rejects_malformed():
    with pytest.raises(ProviderAuthError):
        shopify_auth.verify_shop_domain("not-a-shop-domain.com")


def test_verify_shop_domain_accepts_configured_shop():
    settings = get_settings()
    shopify_auth.verify_shop_domain(settings.shopify_shop_domain)


def test_verify_state_consumes_nonce_once():
    url = shopify_auth.build_authorization_url()
    state = url.split("state=")[1].split("&")[0]

    shopify_auth.verify_state(state)

    with pytest.raises(ProviderAuthError):
        shopify_auth.verify_state(state)


def test_verify_callback_hmac_accepts_valid_signature():
    params = {
        "code": "abc123",
        "shop": "test-shop.myshopify.com",
        "state": "some-state",
        "timestamp": "1700000000",
    }
    shopify_auth.verify_callback_hmac(params, _sign(params))


def test_verify_callback_hmac_rejects_tampered_signature():
    params = {
        "code": "abc123",
        "shop": "test-shop.myshopify.com",
        "state": "some-state",
        "timestamp": "1700000000",
    }
    bad_signature = _sign({**params, "code": "different-code"})

    with pytest.raises(ProviderAuthError):
        shopify_auth.verify_callback_hmac(params, bad_signature)


@respx.mock
async def test_exchange_code_for_token_stores_token():
    settings = get_settings()
    respx.post(
        f"https://{settings.shopify_shop_domain}/admin/oauth/access_token"
    ).mock(
        return_value=Response(
            200, json={"access_token": "shpat-1", "scope": "read_customers"}
        )
    )

    token = await shopify_auth.exchange_code_for_token(
        settings.shopify_shop_domain, "some-code"
    )

    assert token.access_token == "shpat-1"
    assert shopify_auth.load_token().access_token == "shpat-1"


@respx.mock
async def test_exchange_code_for_token_failure_raises_auth_error():
    settings = get_settings()
    respx.post(
        f"https://{settings.shopify_shop_domain}/admin/oauth/access_token"
    ).mock(return_value=Response(400, json={"error": "invalid_request"}))

    with pytest.raises(ProviderAuthError):
        await shopify_auth.exchange_code_for_token(
            settings.shopify_shop_domain, "bad-code"
        )
