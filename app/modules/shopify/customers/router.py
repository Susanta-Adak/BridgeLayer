from fastapi import APIRouter, Query

from app.core.deps import envelope
from app.modules.shopify.customers import service
from app.modules.shopify.customers.schemas import CustomerRequest

router = APIRouter(prefix="/shopify/customers", tags=["Shopify"])


@router.post("", status_code=201)
async def create_customer(payload: CustomerRequest):
    customer = await service.create_customer(payload)
    return envelope(customer)


@router.get("/{customer_id}")
async def get_customer(customer_id: str):
    customer = await service.get_customer(customer_id)
    return envelope(customer)


@router.get("")
async def list_customers(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=250)
):
    result = await service.list_customers(page, per_page)
    return envelope(result)


@router.put("/{customer_id}")
async def update_customer(customer_id: str, payload: CustomerRequest):
    customer = await service.update_customer(customer_id, payload)
    return envelope(customer)
