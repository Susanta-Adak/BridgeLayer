import pytest
import respx
from httpx import Response

from app.core.exceptions import ProviderAuthError
from app.providers.base import BaseCRMProvider


class _DummyProvider(BaseCRMProvider):
    """Minimal concrete provider to exercise the Template Method in

    isolation, without pulling in Zoho/Shopify specifics.
    """

    name = "dummy"

    def __init__(self):
        self.refresh_calls = 0

    async def get_access_token(self):
        return "stale-token"

    async def refresh_token(self):
        self.refresh_calls += 1
        return "fresh-token"

    def is_token_expired(self):
        return False

    def build_auth_headers(self, token):
        return {"Authorization": token}

    async def create_contact(self, contact): ...
    async def get_contact(self, contact_id): ...
    async def list_contacts(self, page, per_page): ...
    async def update_contact(self, contact_id, contact): ...
    async def delete_contact(self, contact_id): ...
    async def create_lead(self, lead): ...
    async def get_lead(self, lead_id): ...
    async def list_leads(self, page, per_page): ...


@respx.mock
async def test_authenticated_request_refreshes_once_on_401():
    route = respx.get("https://example.test/resource")
    route.side_effect = [Response(401), Response(200, json={"ok": True})]

    provider = _DummyProvider()
    response = await provider.authenticated_request(
        "GET", "https://example.test/resource"
    )

    assert response.status_code == 200
    assert provider.refresh_calls == 1


@respx.mock
async def test_authenticated_request_raises_after_second_401():
    respx.get("https://example.test/resource").mock(return_value=Response(401))

    provider = _DummyProvider()
    with pytest.raises(ProviderAuthError):
        await provider.authenticated_request(
            "GET", "https://example.test/resource"
        )

    assert provider.refresh_calls == 1


@respx.mock
async def test_authenticated_request_passes_through_success_without_refresh():
    respx.get("https://example.test/resource").mock(
        return_value=Response(200, json={"ok": True})
    )

    provider = _DummyProvider()
    response = await provider.authenticated_request(
        "GET", "https://example.test/resource"
    )

    assert response.status_code == 200
    assert provider.refresh_calls == 0
