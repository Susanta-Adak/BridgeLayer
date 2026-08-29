"""Exercises app.modules.shopify.customers.service end to end

(mocked Shopify HTTP calls via respx), including the local-mirror
upsert on create/update.
"""

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.session import SessionLocal
from app.modules.shopify.customers import service as customers_service
from app.modules.shopify.customers.models import ShopifyCustomer
from app.modules.shopify.customers.schemas import CustomerRequest


def _admin_base():
    settings = get_settings()
    return (
        f"https://{settings.shopify_shop_domain}"
        f"/admin/api/{settings.shopify_api_version}"
    )


def _local_customer(external_id: str) -> ShopifyCustomer | None:
    with SessionLocal() as db:
        return (
            db.query(ShopifyCustomer)
            .filter(ShopifyCustomer.external_id == external_id)
            .first()
        )


@respx.mock
async def test_create_customer_creates_then_mirrors_locally():
    base = _admin_base()
    respx.post(f"{base}/customers.json").mock(
        return_value=Response(
            201,
            json={
                "customer": {
                    "id": 555,
                    "first_name": "Grace",
                    "last_name": "Hopper",
                    "email": "grace@example.com",
                    "phone": None,
                }
            },
        )
    )

    customer = await customers_service.create_customer(
        CustomerRequest(
            first_name="Grace", last_name="Hopper", email="grace@example.com"
        )
    )

    assert customer.id == "555"
    assert customer.email == "grace@example.com"

    row = _local_customer("555")
    assert row is not None
    assert row.email == "grace@example.com"


@respx.mock
async def test_get_customer_not_found_raises():
    base = _admin_base()
    respx.get(f"{base}/customers/999.json").mock(return_value=Response(404))

    with pytest.raises(NotFoundError):
        await customers_service.get_customer("999")


@respx.mock
async def test_list_customers_detects_has_more_from_link_header():
    base = _admin_base()
    respx.get(f"{base}/customers.json").mock(
        return_value=Response(
            200,
            json={"customers": []},
            headers={
                "Link": f'<{base}/customers.json?page_info=abc>; rel="next"'
            },
        )
    )

    page = await customers_service.list_customers(1, 20)

    assert page.meta.has_more is True


@respx.mock
async def test_update_customer_overwrites_local_snapshot():
    base = _admin_base()
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

    await customers_service.update_customer(
        "502",
        CustomerRequest(
            first_name="Grace",
            last_name="Murray Hopper",
            email="grace@example.com",
        ),
    )

    row = _local_customer("502")
    assert row.last_name == "Murray Hopper"
