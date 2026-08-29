"""Request/response schemas for /shopify/orders."""

from pydantic import BaseModel

from app.core.schemas import PageMeta
from app.modules.shopify.customers.schemas import CustomerResponse


class OrderResponse(BaseModel):
    order_id: str
    customer: CustomerResponse | None = None
    total_price: str
    currency: str
    order_status: str
    created_at: str


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    meta: PageMeta
