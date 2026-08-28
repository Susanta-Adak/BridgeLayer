"""Adapter: translates Shopify's Customer JSON shape into

BridgeLayer's unified `Customer` DTO, and vice versa for writes.
"""

from app.core.exceptions import NotFoundError, ProviderAPIError
from app.providers.schemas import Customer, CustomerInput, Page


def _to_shopify_payload(customer: CustomerInput) -> dict:
    return {
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
    }


def _from_shopify_record(record: dict) -> Customer:
    return Customer(
        id=str(record["id"]),
        first_name=record.get("first_name"),
        last_name=record.get("last_name"),
        email=record.get("email"),
        phone=record.get("phone"),
    )


class ShopifyCustomersMixin:
    """Mixed into ShopifyCommerceProvider; assumes

    self.authenticated_request and self.base_url from the sibling
    client module.
    """

    async def create_customer(self, customer: CustomerInput) -> Customer:
        response = await self.authenticated_request(
            "POST",
            f"{self.base_url}/customers.json",
            json={"customer": _to_shopify_payload(customer)},
        )
        if response.status_code >= 400:
            raise ProviderAPIError(
                "Shopify failed to create customer",
                details={"response": _safe_json(response)},
            )
        return _from_shopify_record(response.json()["customer"])

    async def get_customer(self, customer_id: str) -> Customer:
        response = await self.authenticated_request(
            "GET", f"{self.base_url}/customers/{customer_id}.json"
        )
        if response.status_code == 404:
            raise NotFoundError(f"Shopify customer {customer_id} not found")
        return _from_shopify_record(response.json()["customer"])

    async def list_customers(self, page: int, per_page: int) -> Page:
        response = await self.authenticated_request(
            "GET",
            f"{self.base_url}/customers.json",
            params={"limit": per_page},
        )
        body = response.json()
        items = [_from_shopify_record(r) for r in body.get("customers", [])]
        has_more = 'rel="next"' in response.headers.get("Link", "")
        return Page(
            items=items, page=page, per_page=per_page, has_more=has_more
        )

    async def update_customer(
        self, customer_id: str, customer: CustomerInput
    ) -> Customer:
        response = await self.authenticated_request(
            "PUT",
            f"{self.base_url}/customers/{customer_id}.json",
            json={"customer": _to_shopify_payload(customer)},
        )
        if response.status_code == 404:
            raise NotFoundError(f"Shopify customer {customer_id} not found")
        if response.status_code >= 400:
            raise ProviderAPIError(
                "Shopify failed to update customer",
                details={"response": _safe_json(response)},
            )
        return _from_shopify_record(response.json()["customer"])


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return response.text
