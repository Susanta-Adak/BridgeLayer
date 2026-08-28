"""Provider abstraction layer.

`BaseProvider` implements the Template Method for authenticated
requests: build a URL, attach auth, send, and on a 401 refresh the
token once and retry. Concrete providers only fill in the
auth-specific hooks (`get_access_token`, `refresh_token`,
`is_token_expired`, `build_auth_headers`) - the retry/refresh
sequence itself never changes.

`BaseCRMProvider` and `BaseCommerceProvider` are the Strategy
interfaces routes/services depend on. Zoho, Shopify, and any future
provider are interchangeable implementations of these contracts;
nothing outside `providers/` ever imports a concrete class.
"""

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.exceptions import ProviderAuthError
from app.core.http_client import request_with_retry
from app.providers.schemas import (
    Contact,
    ContactInput,
    Customer,
    CustomerInput,
    Lead,
    LeadInput,
    Order,
    Page,
)


class BaseProvider(ABC):
    """Shared Template Method skeleton for authenticated HTTP calls."""

    name: str

    @abstractmethod
    async def get_access_token(self) -> str:
        """Return a currently-valid access token, without a network

        call if one is already cached and unexpired.
        """

    @abstractmethod
    async def refresh_token(self) -> str:
        """Force a token refresh and return the new access token."""

    @abstractmethod
    def is_token_expired(self) -> bool: ...

    @abstractmethod
    def build_auth_headers(self, token: str) -> dict[str, str]: ...

    async def authenticated_request(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """The template: get/refresh a token, send, retry once on 401."""
        token = await self.get_access_token()
        if self.is_token_expired():
            token = await self.refresh_token()

        response = await self._send(method, url, token, **kwargs)

        if response.status_code == 401:
            token = await self.refresh_token()
            response = await self._send(method, url, token, **kwargs)
            if response.status_code == 401:
                raise ProviderAuthError(
                    f"{self.name}: authentication failed after token "
                    "refresh"
                )

        return response

    async def _send(
        self, method: str, url: str, token: str, **kwargs: Any
    ) -> httpx.Response:
        headers = {
            **kwargs.pop("headers", {}),
            **self.build_auth_headers(token),
        }
        return await request_with_retry(
            method, url, headers=headers, **kwargs
        )


class BaseCRMProvider(BaseProvider):
    """Strategy interface implemented by every CRM provider."""

    @abstractmethod
    async def create_contact(self, contact: ContactInput) -> Contact: ...

    @abstractmethod
    async def get_contact(self, contact_id: str) -> Contact: ...

    @abstractmethod
    async def list_contacts(self, page: int, per_page: int) -> Page: ...

    @abstractmethod
    async def update_contact(
        self, contact_id: str, contact: ContactInput
    ) -> Contact: ...

    @abstractmethod
    async def delete_contact(self, contact_id: str) -> None: ...

    @abstractmethod
    async def create_lead(self, lead: LeadInput) -> Lead: ...

    @abstractmethod
    async def get_lead(self, lead_id: str) -> Lead: ...

    @abstractmethod
    async def list_leads(self, page: int, per_page: int) -> Page: ...


class BaseCommerceProvider(BaseProvider):
    """Strategy interface implemented by every commerce provider."""

    @abstractmethod
    async def create_customer(self, customer: CustomerInput) -> Customer: ...

    @abstractmethod
    async def get_customer(self, customer_id: str) -> Customer: ...

    @abstractmethod
    async def list_customers(self, page: int, per_page: int) -> Page: ...

    @abstractmethod
    async def update_customer(
        self, customer_id: str, customer: CustomerInput
    ) -> Customer: ...

    @abstractmethod
    async def list_orders(self, page: int, per_page: int) -> Page: ...

    @abstractmethod
    async def get_order(self, order_id: str) -> Order: ...
