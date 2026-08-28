import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.providers.schemas import ContactInput, LeadInput
from app.providers.zoho import auth as zoho_auth
from app.providers.zoho.client import ZohoCRMProvider


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
                        "message": "record added",
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

    provider = ZohoCRMProvider()
    contact = await provider.create_contact(
        ContactInput(
            first_name="Ada", last_name="Lovelace", email="ada@example.com"
        )
    )

    assert contact.id == "111"
    assert contact.first_name == "Ada"
    assert contact.email == "ada@example.com"


@respx.mock
async def test_get_contact_not_found_raises():
    base = _crm_base()
    respx.get(f"{base}/Contacts/999").mock(
        return_value=Response(200, json={"data": []})
    )

    provider = ZohoCRMProvider()
    with pytest.raises(NotFoundError):
        await provider.get_contact("999")


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

    provider = ZohoCRMProvider()
    page = await provider.list_contacts(1, 20)

    assert len(page.items) == 1
    assert page.has_more is True


@respx.mock
async def test_delete_contact_success():
    base = _crm_base()
    respx.delete(f"{base}/Contacts/111").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "code": "SUCCESS",
                        "status": "success",
                        "message": "record deleted",
                        "details": {"id": "111"},
                    }
                ]
            },
        )
    )

    provider = ZohoCRMProvider()
    await provider.delete_contact("111")  # should not raise


@respx.mock
async def test_create_lead_creates_then_fetches_record():
    base = _crm_base()
    respx.post(f"{base}/Leads").mock(
        return_value=Response(
            201,
            json={
                "data": [
                    {
                        "code": "SUCCESS",
                        "status": "success",
                        "message": "record added",
                        "details": {"id": "222"},
                    }
                ]
            },
        )
    )
    respx.get(f"{base}/Leads/222").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "222",
                        "First_Name": "Grace",
                        "Last_Name": "Hopper",
                        "Email": "grace@example.com",
                        "Company": "Navy",
                        "Lead_Source": "Web",
                    }
                ]
            },
        )
    )

    provider = ZohoCRMProvider()
    lead = await provider.create_lead(
        LeadInput(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            company="Navy",
            lead_source="Web",
        )
    )

    assert lead.id == "222"
    assert lead.lead_source == "Web"
