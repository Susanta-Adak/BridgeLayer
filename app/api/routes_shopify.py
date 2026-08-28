from fastapi import APIRouter, Query

from app.api.deps import envelope
from app.api.schemas import (
    CustomerListResponse,
    CustomerRequest,
    CustomerResponse,
    OrderListResponse,
    OrderResponse,
    PageMeta,
)
from app.providers.schemas import CustomerInput
from app.services import shopify_service

router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.post("/customers", status_code=201)
async def create_customer(payload: CustomerRequest):
    customer = await shopify_service.create_customer(
        CustomerInput(**payload.model_dump())
    )
    return envelope(CustomerResponse(**customer.model_dump()))


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    customer = await shopify_service.get_customer(customer_id)
    return envelope(CustomerResponse(**customer.model_dump()))


@router.get("/customers")
async def list_customers(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=250)
):
    result = await shopify_service.list_customers(page, per_page)
    return envelope(
        CustomerListResponse(
            items=[CustomerResponse(**c.model_dump()) for c in result.items],
            meta=PageMeta(
                page=result.page,
                per_page=result.per_page,
                has_more=result.has_more,
            ),
        )
    )


@router.put("/customers/{customer_id}")
async def update_customer(customer_id: str, payload: CustomerRequest):
    customer = await shopify_service.update_customer(
        customer_id, CustomerInput(**payload.model_dump())
    )
    return envelope(CustomerResponse(**customer.model_dump()))


@router.get("/orders")
async def list_orders(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=250)
):
    result = await shopify_service.list_orders(page, per_page)
    return envelope(
        OrderListResponse(
            items=[
                OrderResponse(
                    order_id=o.order_id,
                    customer=CustomerResponse(**o.customer.model_dump())
                    if o.customer
                    else None,
                    total_price=o.total_price,
                    currency=o.currency,
                    order_status=o.order_status,
                    created_at=o.created_at,
                )
                for o in result.items
            ],
            meta=PageMeta(
                page=result.page,
                per_page=result.per_page,
                has_more=result.has_more,
            ),
        )
    )


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await shopify_service.get_order(order_id)
    return envelope(
        OrderResponse(
            order_id=order.order_id,
            customer=CustomerResponse(**order.customer.model_dump())
            if order.customer
            else None,
            total_price=order.total_price,
            currency=order.currency,
            order_status=order.order_status,
            created_at=order.created_at,
        )
    )
