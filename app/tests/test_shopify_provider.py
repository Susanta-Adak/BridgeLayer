import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.providers.schemas import CustomerInput
from app.providers.shopify.client import ShopifyCommerceProvider


def _admin_base():
    settings = get_settings()
    return (
        f"https://{settings.shopify_shop_domain}"
        f"/admin/api/{settings.shopify_api_version}"
    )


@respx.mock
async def test_create_customer_returns_mapped_dto():
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

    provider = ShopifyCommerceProvider()
    customer = await provider.create_customer(
        CustomerInput(
            first_name="Grace", last_name="Hopper", email="grace@example.com"
        )
    )

    assert customer.id == "555"
    assert customer.email == "grace@example.com"


@respx.mock
async def test_get_customer_not_found_raises():
    base = _admin_base()
    respx.get(f"{base}/customers/999.json").mock(return_value=Response(404))

    provider = ShopifyCommerceProvider()
    with pytest.raises(NotFoundError):
        await provider.get_customer("999")


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

    provider = ShopifyCommerceProvider()
    page = await provider.list_customers(1, 20)

    assert page.has_more is True


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

    provider = ShopifyCommerceProvider()
    page = await provider.list_orders(1, 20)

    assert len(page.items) == 1
    order = page.items[0]
    assert order.order_id == "9001"
    assert order.order_status == "paid"
    assert order.customer.email == "grace@example.com"


@respx.mock
async def test_get_order_not_found_raises():
    base = _admin_base()
    respx.get(f"{base}/orders/1.json").mock(return_value=Response(404))

    provider = ShopifyCommerceProvider()
    with pytest.raises(NotFoundError):
        await provider.get_order("1")
