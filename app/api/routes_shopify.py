from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from app.api.deps import envelope
from app.api.schemas import (
    AuthUrlResponse,
    CustomerListResponse,
    CustomerRequest,
    CustomerResponse,
    OrderListResponse,
    OrderResponse,
    PageMeta,
)
from app.core.exceptions import ValidationError
from app.providers.schemas import CustomerInput
from app.services import shopify_service

router = APIRouter(prefix="/shopify", tags=["shopify"])


@router.get("/auth/authorize")
async def authorize():
    url = shopify_service.get_authorization_url()
    return envelope(AuthUrlResponse(authorization_url=url))


@router.get("/auth/authorize/redirect")
async def authorize_redirect():
    """Convenience endpoint: redirect the browser straight to Shopify."""
    return RedirectResponse(shopify_service.get_authorization_url())


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Shopify signs every query param it sends (which can include

    extras like `host` depending on app type), so the HMAC has to be
    verified over whatever was actually sent - not a hardcoded
    subset of fields.
    """
    params = dict(request.query_params)
    hmac_signature = params.pop("hmac", None)
    params.pop("signature", None)
    if not hmac_signature:
        raise ValidationError("Missing hmac query parameter")

    await shopify_service.handle_oauth_callback(
        params=params, hmac_signature=hmac_signature
    )
    return envelope({"authorized": True})


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
