"""DemoCRMProvider: a stub third provider with no real backend.

It exists purely to demonstrate the extensibility claim in
CLAUDE.md - implementing `BaseCRMProvider` and registering with
`ProviderFactory` is the entire integration surface; nothing in
`api/`, `db/`, or the Zoho/Shopify code changes.

Since there's no real API to call, it keeps an in-memory store and
skips the HTTP Template Method entirely - but it still satisfies the
same Strategy interface as Zoho, so `services/demo_service.py` and
`api/routes_demo.py` are as thin as their Zoho counterparts.
"""

import itertools

from app.core.exceptions import NotFoundError
from app.providers.base import BaseCRMProvider
from app.providers.schemas import Contact, ContactInput, Lead, LeadInput, Page

_contacts: dict[str, Contact] = {}
_leads: dict[str, Lead] = {}
_contact_ids = itertools.count(1)
_lead_ids = itertools.count(1)


class DemoCRMProvider(BaseCRMProvider):
    name = "demo"

    async def get_access_token(self) -> str:
        return "demo-token"

    async def refresh_token(self) -> str:
        return "demo-token"

    def is_token_expired(self) -> bool:
        return False

    def build_auth_headers(self, token: str) -> dict[str, str]:
        return {}

    async def create_contact(self, contact: ContactInput) -> Contact:
        contact_id = str(next(_contact_ids))
        record = Contact(id=contact_id, **contact.model_dump())
        _contacts[contact_id] = record
        return record

    async def get_contact(self, contact_id: str) -> Contact:
        try:
            return _contacts[contact_id]
        except KeyError:
            raise NotFoundError(
                f"Demo contact {contact_id} not found"
            ) from None

    async def list_contacts(self, page: int, per_page: int) -> Page:
        values = list(_contacts.values())
        start = (page - 1) * per_page
        chunk = values[start : start + per_page]
        return Page(
            items=chunk,
            page=page,
            per_page=per_page,
            has_more=start + per_page < len(values),
        )

    async def update_contact(
        self, contact_id: str, contact: ContactInput
    ) -> Contact:
        if contact_id not in _contacts:
            raise NotFoundError(f"Demo contact {contact_id} not found")
        record = Contact(id=contact_id, **contact.model_dump())
        _contacts[contact_id] = record
        return record

    async def delete_contact(self, contact_id: str) -> None:
        if _contacts.pop(contact_id, None) is None:
            raise NotFoundError(f"Demo contact {contact_id} not found")

    async def create_lead(self, lead: LeadInput) -> Lead:
        lead_id = str(next(_lead_ids))
        record = Lead(id=lead_id, **lead.model_dump())
        _leads[lead_id] = record
        return record

    async def get_lead(self, lead_id: str) -> Lead:
        try:
            return _leads[lead_id]
        except KeyError:
            raise NotFoundError(f"Demo lead {lead_id} not found") from None

    async def list_leads(self, page: int, per_page: int) -> Page:
        values = list(_leads.values())
        start = (page - 1) * per_page
        chunk = values[start : start + per_page]
        return Page(
            items=chunk,
            page=page,
            per_page=per_page,
            has_more=start + per_page < len(values),
        )
