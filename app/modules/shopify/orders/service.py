"""Facade for Shopify Orders.

Calls the Shopify API via client.py, adapts Shopify's JSON shape to
OrderResponse, and mirrors every order BridgeLayer reads into the
local shopify_orders table (orders are read-only here, so list/get
is the only place a local copy can be taken).
"""

from app.core.exceptions import NotFoundError
from app.core.schemas import PageMeta
from app.db.session import SessionLocal
from app.modules.shopify import client as shopify_client
from app.modules.shopify.customers.schemas import CustomerResponse
from app.modules.shopify.orders.models import ShopifyOrder
from app.modules.shopify.orders.schemas import OrderListResponse, OrderResponse


def _from_shopify_record(record: dict) -> OrderResponse:
    customer_raw = record.get("customer")
    customer = None
    if customer_raw:
        customer = CustomerResponse(
            id=str(customer_raw["id"]),
            first_name=customer_raw.get("first_name"),
            last_name=customer_raw.get("last_name"),
            email=customer_raw.get("email"),
            phone=customer_raw.get("phone"),
        )
    return OrderResponse(
        order_id=str(record["id"]),
        customer=customer,
        total_price=record.get("total_price", "0.00"),
        currency=record.get("currency", ""),
        order_status=record.get("financial_status", "unknown"),
        created_at=record.get("created_at", ""),
    )


def _save_local(order: OrderResponse) -> None:
    with SessionLocal() as db:
        row = (
            db.query(ShopifyOrder)
            .filter(ShopifyOrder.external_id == order.order_id)
            .first()
        )
        if row is None:
            row = ShopifyOrder(external_id=order.order_id)
            db.add(row)
        row.customer_external_id = (
            order.customer.id if order.customer else None
        )
        row.customer_email = order.customer.email if order.customer else None
        row.total_price = order.total_price
        row.currency = order.currency
        row.order_status = order.order_status
        row.order_created_at = order.created_at
        db.commit()


async def list_orders(page: int, per_page: int) -> OrderListResponse:
    response = await shopify_client.authenticated_request(
        "GET",
        f"{shopify_client.base_url()}/orders.json",
        params={"limit": per_page, "status": "any"},
    )
    body = response.json()
    items = [_from_shopify_record(r) for r in body.get("orders", [])]
    for order in items:
        _save_local(order)
    has_more = 'rel="next"' in response.headers.get("Link", "")
    return OrderListResponse(
        items=items,
        meta=PageMeta(page=page, per_page=per_page, has_more=has_more),
    )


async def get_order(order_id: str) -> OrderResponse:
    response = await shopify_client.authenticated_request(
        "GET", f"{shopify_client.base_url()}/orders/{order_id}.json"
    )
    if response.status_code == 404:
        raise NotFoundError(f"Shopify order {order_id} not found")
    order = _from_shopify_record(response.json()["order"])
    _save_local(order)
    return order
