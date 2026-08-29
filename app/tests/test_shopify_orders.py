"""Exercises app.modules.shopify.orders.service end to end (mocked

Shopify HTTP calls via respx). Orders are read-only in this API and
Shopify stays the source of truth.
"""

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.modules.shopify.orders import service as orders_service


def _admin_base():
    settings = get_settings()
    return (
        f"https://{settings.shopify_shop_domain}"
        f"/admin/api/{settings.shopify_api_version}"
    )


@respx.mock
async def test_list_orders_maps_order_and_nested_customer():
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


@respx.mock
async def test_get_order_not_found_raises():
    base = _admin_base()
    respx.get(f"{base}/orders/1.json").mock(return_value=Response(404))

    with pytest.raises(NotFoundError):
        await orders_service.get_order("1")
