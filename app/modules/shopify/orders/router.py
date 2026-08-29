from fastapi import APIRouter, Query

from app.core.deps import envelope
from app.modules.shopify.orders import service

router = APIRouter(prefix="/shopify/orders", tags=["Shopify"])


@router.get("")
async def list_orders(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=250)
):
    result = await service.list_orders(page, per_page)
    return envelope(result)


@router.get("/{order_id}")
async def get_order(order_id: str):
    order = await service.get_order(order_id)
    return envelope(order)
