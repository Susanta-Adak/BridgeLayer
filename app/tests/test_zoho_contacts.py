"""Exercises app.modules.zoho.contacts.service end to end (mocked

Zoho HTTP calls via respx). Zoho is the source of truth for contact
data, so these tests only verify the request/response mapping and
error handling - there is no local copy to assert against.
"""

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.modules.zoho.auth import service as zoho_auth
from app.modules.zoho.contacts import service as contacts_service
from app.modules.zoho.contacts.schemas import ContactRequest


@pytest.fixture(autouse=True)
def _seed_token():
    zoho_auth._save_token(
        {
            "access_token": "seeded-access-token",
            "refresh_token": "seeded-refresh-token",
            "expires_in": 3600,
        },
        require_refresh_token=True,
    )


def _crm_base():
    settings = get_settings()
    return f"{settings.zoho_api_base_url}/crm/v3"


@respx.mock
async def test_create_contact_creates_then_fetches_record():
    base = _crm_base()
    respx.post(f"{base}/Contacts").mock(
        return_value=Response(
            201,
            json={
                "data": [
                    {
                        "code": "SUCCESS",
                        "status": "success",
                        "details": {"id": "111"},
                    }
                ]
            },
        )
    )
    respx.get(f"{base}/Contacts/111").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "111",
                        "First_Name": "Ada",
                        "Last_Name": "Lovelace",
                        "Email": "ada@example.com",
                        "Phone": None,
                        "Account_Name": None,
                    }
                ]
            },
        )
    )

    contact = await contacts_service.create_contact(
        ContactRequest(
            first_name="Ada", last_name="Lovelace", email="ada@example.com"
        )
    )

    assert contact.id == "111"
    assert contact.email == "ada@example.com"


@respx.mock
async def test_get_contact_not_found_raises():
    base = _crm_base()
    respx.get(f"{base}/Contacts/999").mock(
        return_value=Response(200, json={"data": []})
    )

    with pytest.raises(NotFoundError):
        await contacts_service.get_contact("999")


@respx.mock
async def test_list_contacts_maps_pagination_info():
    base = _crm_base()
    respx.get(f"{base}/Contacts").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "1",
                        "First_Name": "Ada",
                        "Last_Name": "Lovelace",
                        "Email": "ada@example.com",
                    }
                ],
                "info": {"page": 1, "per_page": 20, "more_records": True},
            },
        )
    )

    page = await contacts_service.list_contacts(1, 20)

    assert len(page.items) == 1
    assert page.meta.has_more is True


@respx.mock
async def test_update_contact_returns_updated_record():
    base = _crm_base()
    respx.put(f"{base}/Contacts/302").mock(
        return_value=Response(
            200, json={"data": [{"code": "SUCCESS", "status": "success"}]}
        )
    )
    respx.get(f"{base}/Contacts/302").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "302",
                        "First_Name": "Ada",
                        "Last_Name": "Byron",
                        "Email": "ada.byron@example.com",
                    }
                ]
            },
        )
    )

    contact = await contacts_service.update_contact(
        "302",
        ContactRequest(
            first_name="Ada",
            last_name="Byron",
            email="ada.byron@example.com",
        ),
    )

    assert contact.last_name == "Byron"


@respx.mock
async def test_delete_contact_success():
    base = _crm_base()
    respx.delete(f"{base}/Contacts/111").mock(
        return_value=Response(
            200,
            json={"data": [{"code": "SUCCESS", "status": "success"}]},
        )
    )

    await contacts_service.delete_contact("111")  # should not raise
