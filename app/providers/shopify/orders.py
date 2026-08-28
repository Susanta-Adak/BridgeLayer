"""Adapter: translates Shopify's Order JSON shape into

BridgeLayer's unified `Order` DTO.
"""

from app.core.exceptions import NotFoundError
from app.providers.schemas import Customer, Order, Page


def _from_shopify_record(record: dict) -> Order:
    customer_raw = record.get("customer")
    customer = None
    if customer_raw:
        customer = Customer(
            id=str(customer_raw["id"]),
            first_name=customer_raw.get("first_name"),
            last_name=customer_raw.get("last_name"),
            email=customer_raw.get("email"),
            phone=customer_raw.get("phone"),
        )
    return Order(
        order_id=str(record["id"]),
        customer=customer,
        total_price=record.get("total_price", "0.00"),
        currency=record.get("currency", ""),
        order_status=record.get("financial_status", "unknown"),
        created_at=record.get("created_at", ""),
    )


class ShopifyOrdersMixin:
    """Mixed into ShopifyCommerceProvider; assumes

    self.authenticated_request and self.base_url from the sibling
    client module.
    """

    async def list_orders(self, page: int, per_page: int) -> Page:
        response = await self.authenticated_request(
            "GET",
            f"{self.base_url}/orders.json",
            params={"limit": per_page, "status": "any"},
        )
        body = response.json()
        items = [_from_shopify_record(r) for r in body.get("orders", [])]
        has_more = 'rel="next"' in response.headers.get("Link", "")
        return Page(
            items=items, page=page, per_page=per_page, has_more=has_more
        )

    async def get_order(self, order_id: str) -> Order:
        response = await self.authenticated_request(
            "GET", f"{self.base_url}/orders/{order_id}.json"
        )
        if response.status_code == 404:
            raise NotFoundError(f"Shopify order {order_id} not found")
        return _from_shopify_record(response.json()["order"])
