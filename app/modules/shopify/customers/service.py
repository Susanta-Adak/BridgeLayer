"""Facade for Shopify Customers.

Calls the Shopify API via client.py, adapts Shopify's JSON shape
to/from CustomerRequest/CustomerResponse, and mirrors every create/
update into the local shopify_customers table so BridgeLayer keeps
its own durable copy of what it sent - not just a pass-through API
call.
"""

from app.core.exceptions import NotFoundError, ProviderAPIError
from app.core.schemas import PageMeta
from app.db.session import SessionLocal
from app.modules.shopify import client as shopify_client
from app.modules.shopify.customers.models import ShopifyCustomer
from app.modules.shopify.customers.schemas import (
    CustomerListResponse,
    CustomerRequest,
    CustomerResponse,
)


def _to_shopify_payload(customer: CustomerRequest) -> dict:
    return {
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
    }


def _from_shopify_record(record: dict) -> CustomerResponse:
    return CustomerResponse(
        id=str(record["id"]),
        first_name=record.get("first_name"),
        last_name=record.get("last_name"),
        email=record.get("email"),
        phone=record.get("phone"),
    )


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return response.text


def _save_local(customer: CustomerResponse) -> None:
    with SessionLocal() as db:
        row = (
            db.query(ShopifyCustomer)
            .filter(ShopifyCustomer.external_id == customer.id)
            .first()
        )
        if row is None:
            row = ShopifyCustomer(external_id=customer.id)
            db.add(row)
        row.first_name = customer.first_name
        row.last_name = customer.last_name
        row.email = customer.email
        row.phone = customer.phone
        db.commit()


async def create_customer(data: CustomerRequest) -> CustomerResponse:
    response = await shopify_client.authenticated_request(
        "POST",
        f"{shopify_client.base_url()}/customers.json",
        json={"customer": _to_shopify_payload(data)},
    )
    if response.status_code >= 400:
        raise ProviderAPIError(
            "Shopify failed to create customer",
            details={"response": _safe_json(response)},
        )
    customer = _from_shopify_record(response.json()["customer"])
    _save_local(customer)
    return customer


async def get_customer(customer_id: str) -> CustomerResponse:
    response = await shopify_client.authenticated_request(
        "GET", f"{shopify_client.base_url()}/customers/{customer_id}.json"
    )
    if response.status_code == 404:
        raise NotFoundError(f"Shopify customer {customer_id} not found")
    return _from_shopify_record(response.json()["customer"])


async def list_customers(page: int, per_page: int) -> CustomerListResponse:
    response = await shopify_client.authenticated_request(
        "GET",
        f"{shopify_client.base_url()}/customers.json",
        params={"limit": per_page},
    )
    body = response.json()
    items = [_from_shopify_record(r) for r in body.get("customers", [])]
    has_more = 'rel="next"' in response.headers.get("Link", "")
    return CustomerListResponse(
        items=items,
        meta=PageMeta(page=page, per_page=per_page, has_more=has_more),
    )


async def update_customer(
    customer_id: str, data: CustomerRequest
) -> CustomerResponse:
    response = await shopify_client.authenticated_request(
        "PUT",
        f"{shopify_client.base_url()}/customers/{customer_id}.json",
        json={"customer": _to_shopify_payload(data)},
    )
    if response.status_code == 404:
        raise NotFoundError(f"Shopify customer {customer_id} not found")
    if response.status_code >= 400:
        raise ProviderAPIError(
            "Shopify failed to update customer",
            details={"response": _safe_json(response)},
        )
    customer = _from_shopify_record(response.json()["customer"])
    _save_local(customer)
    return customer
