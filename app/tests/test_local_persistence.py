"""Every create/update/delete a service sends to a provider must

also be mirrored into the local `integration_records` table via
`app.db.repository`, so BridgeLayer keeps its own durable copy
instead of only trusting the third party's. Exercised through the
service Facades (not the repository directly) so these tests also
prove the mirroring is actually wired in, not just that the
repository functions work in isolation.
"""

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.db import repository
from app.providers.schemas import ContactInput, CustomerInput, LeadInput
from app.providers.zoho import auth as zoho_auth
from app.services import shopify_service, zoho_service


@pytest.fixture(autouse=True)
def _seed_zoho_token():
    zoho_auth._save_token(
        {
            "access_token": "seeded-access-token",
            "refresh_token": "seeded-refresh-token",
            "expires_in": 3600,
        },
        require_refresh_token=True,
    )


def _zoho_base():
    settings = get_settings()
    return f"{settings.zoho_api_base_url}/crm/v3"


def _shopify_base():
    settings = get_settings()
    return (
        f"https://{settings.shopify_shop_domain}"
        f"/admin/api/{settings.shopify_api_version}"
    )


@respx.mock
async def test_create_contact_mirrors_to_local_db():
    base = _zoho_base()
    respx.post(f"{base}/Contacts").mock(
        return_value=Response(
            201,
            json={
                "data": [
                    {
                        "code": "SUCCESS",
                        "status": "success",
                        "details": {"id": "301"},
                    }
                ]
            },
        )
    )
    respx.get(f"{base}/Contacts/301").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "301",
                        "First_Name": "Ada",
                        "Last_Name": "Lovelace",
                        "Email": "ada@example.com",
                    }
                ]
            },
        )
    )

    await zoho_service.create_contact(
        ContactInput(
            first_name="Ada", last_name="Lovelace", email="ada@example.com"
        )
    )

    record = repository.get_record("zoho", "contact", "301")
    assert record is not None
    assert record.is_deleted is False
    assert record.data["email"] == "ada@example.com"


@respx.mock
async def test_update_contact_overwrites_local_snapshot():
    base = _zoho_base()
    respx.put(f"{base}/Contacts/302").mock(
        return_value=Response(
            200,
            json={
                "data": [{"code": "SUCCESS", "status": "success"}],
            },
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

    await zoho_service.update_contact(
        "302",
        ContactInput(
            first_name="Ada",
            last_name="Byron",
            email="ada.byron@example.com",
        ),
    )

    record = repository.get_record("zoho", "contact", "302")
    assert record.data["last_name"] == "Byron"


@respx.mock
async def test_delete_contact_marks_local_record_deleted():
    base = _zoho_base()
    respx.get(f"{base}/Contacts/303").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "303",
                        "First_Name": "Grace",
                        "Last_Name": "Hopper",
                        "Email": "grace@example.com",
                    }
                ]
            },
        )
    )
    respx.delete(f"{base}/Contacts/303").mock(
        return_value=Response(
            200,
            json={"data": [{"code": "SUCCESS", "status": "success"}]},
        )
    )

    await zoho_service.get_contact("303")  # seed a record via a read
    record = repository.get_record("zoho", "contact", "303")
    assert record is None  # get_contact doesn't mirror, only writes do

    repository.upsert_record(
        "zoho", "contact", "303", {"id": "303", "email": "grace@example.com"}
    )
    await zoho_service.delete_contact("303")

    record = repository.get_record("zoho", "contact", "303")
    assert record.is_deleted is True


@respx.mock
async def test_create_lead_mirrors_to_local_db():
    base = _zoho_base()
    respx.post(f"{base}/Leads").mock(
        return_value=Response(
            201,
            json={
                "data": [
                    {
                        "code": "SUCCESS",
                        "status": "success",
                        "details": {"id": "401"},
                    }
                ]
            },
        )
    )
    respx.get(f"{base}/Leads/401").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "401",
                        "First_Name": "Grace",
                        "Last_Name": "Hopper",
                        "Email": "grace@example.com",
                        "Lead_Source": "Web",
                    }
                ]
            },
        )
    )

    await zoho_service.create_lead(
        LeadInput(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            lead_source="Web",
        )
    )

    record = repository.get_record("zoho", "lead", "401")
    assert record is not None
    assert record.data["lead_source"] == "Web"


@respx.mock
async def test_create_customer_mirrors_to_local_db():
    base = _shopify_base()
    respx.post(f"{base}/customers.json").mock(
        return_value=Response(
            201,
            json={
                "customer": {
                    "id": 501,
                    "first_name": "Grace",
                    "last_name": "Hopper",
                    "email": "grace@example.com",
                    "phone": None,
                }
            },
        )
    )

    await shopify_service.create_customer(
        CustomerInput(
            first_name="Grace", last_name="Hopper", email="grace@example.com"
        )
    )

    record = repository.get_record("shopify", "customer", "501")
    assert record is not None
    assert record.data["email"] == "grace@example.com"


@respx.mock
async def test_update_customer_overwrites_local_snapshot():
    base = _shopify_base()
    respx.put(f"{base}/customers/502.json").mock(
        return_value=Response(
            200,
            json={
                "customer": {
                    "id": 502,
                    "first_name": "Grace",
                    "last_name": "Murray Hopper",
                    "email": "grace@example.com",
                    "phone": None,
                }
            },
        )
    )

    await shopify_service.update_customer(
        "502",
        CustomerInput(
            first_name="Grace",
            last_name="Murray Hopper",
            email="grace@example.com",
        ),
    )

    record = repository.get_record("shopify", "customer", "502")
    assert record.data["last_name"] == "Murray Hopper"


def test_upsert_then_mark_deleted_roundtrip():
    repository.upsert_record("demo", "widget", "w1", {"id": "w1"})
    record = repository.get_record("demo", "widget", "w1")
    assert record.is_deleted is False

    repository.mark_deleted("demo", "widget", "w1")
    record = repository.get_record("demo", "widget", "w1")
    assert record.is_deleted is True

    repository.upsert_record("demo", "widget", "w1", {"id": "w1", "v": 2})
    record = repository.get_record("demo", "widget", "w1")
    assert record.is_deleted is False
    assert record.data["v"] == 2
