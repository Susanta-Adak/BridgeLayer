import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import ProviderAuthError
from app.providers.zoho import auth as zoho_auth


@respx.mock
async def test_exchange_code_for_token_stores_tokens():
    settings = get_settings()
    respx.post(f"{settings.zoho_accounts_base_url}/oauth/v2/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "at-1",
                "refresh_token": "rt-1",
                "expires_in": 3600,
            },
        )
    )

    token = await zoho_auth.exchange_code_for_token("some-code")

    assert token.access_token == "at-1"
    assert token.refresh_token == "rt-1"
    assert zoho_auth.load_token().access_token == "at-1"


@respx.mock
async def test_exchange_code_for_token_failure_raises_auth_error():
    settings = get_settings()
    respx.post(f"{settings.zoho_accounts_base_url}/oauth/v2/token").mock(
        return_value=Response(400, json={"error": "invalid_code"})
    )

    with pytest.raises(ProviderAuthError):
        await zoho_auth.exchange_code_for_token("bad-code")


@respx.mock
async def test_refresh_access_token_updates_access_token_keeps_refresh():
    settings = get_settings()
    respx.post(f"{settings.zoho_accounts_base_url}/oauth/v2/token").mock(
        return_value=Response(
            200,
            json={
                "access_token": "at-seed",
                "refresh_token": "rt-seed",
                "expires_in": 3600,
            },
        )
    )
    await zoho_auth.exchange_code_for_token("seed-code")

    respx.post(f"{settings.zoho_accounts_base_url}/oauth/v2/token").mock(
        return_value=Response(
            200, json={"access_token": "at-2", "expires_in": 3600}
        )
    )
    token = await zoho_auth.refresh_access_token("rt-seed")

    assert token.access_token == "at-2"
    assert token.refresh_token == "rt-seed"


def test_build_authorization_url_includes_client_id_and_redirect():
    settings = get_settings()
    url = zoho_auth.build_authorization_url()

    assert settings.zoho_client_id in url
    assert "response_type=code" in url
