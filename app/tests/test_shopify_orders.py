"""Exercises app.modules.shopify.orders.service end to end (mocked

Shopify HTTP calls via respx), including the local-mirror upsert on
every list/get - orders are read-only, so that's the only place a
local copy can be taken.
"""

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.db.session import SessionLocal
from app.modules.shopify.orders import service as orders_service
from app.modules.shopify.orders.models import ShopifyOrder


def _admin_base():
    settings = get_settings()
    return (
        f"https://{settings.shopify_shop_domain}"
        f"/admin/api/{settings.shopify_api_version}"
    )


@respx.mock
async def test_list_orders_maps_order_and_mirrors_locally():
    base = _admin_base()
    respx.get(f"{base}/orders.json").mock(
        return_value=Response(
            200,
            json={
                "orders": [
                    {
                        "id": 9001,
                        "total_price": "42.00",
                        "currency": "USD",
                        "financial_status": "paid",
                        "created_at": "2026-08-01T00:00:00Z",
                        "customer": {
                            "id": 555,
                            "first_name": "Grace",
                            "last_name": "Hopper",
                            "email": "grace@example.com",
                            "phone": None,
                        },
                    }
                ]
            },
        )
    )

    page = await orders_service.list_orders(1, 20)

    assert len(page.items) == 1
    order = page.items[0]
    assert order.order_id == "9001"
    assert order.order_status == "paid"
    assert order.customer.email == "grace@example.com"

    with SessionLocal() as db:
        row = (
            db.query(ShopifyOrder)
            .filter(ShopifyOrder.external_id == "9001")
            .first()
        )
    assert row is not None
    assert row.customer_email == "grace@example.com"
    assert row.total_price == "42.00"


@respx.mock
async def test_get_order_not_found_raises():
    base = _admin_base()
    respx.get(f"{base}/orders/1.json").mock(return_value=Response(404))

    with pytest.raises(NotFoundError):
        await orders_service.get_order("1")
