"""Facade over the Zoho provider.

Routes call one method here; this coordinates provider lookup via
the factory, delegates to the provider's Adapter methods, and is the
single place Zoho-specific orchestration would grow (e.g. caching)
without `api/` ever knowing a provider exists.
"""

from app.db import repository
from app.providers.factory import ProviderFactory
from app.providers.schemas import Contact, ContactInput, Lead, LeadInput, Page
from app.providers.zoho import auth as zoho_auth
from app.providers.zoho.client import ZohoCRMProvider

_PROVIDER = "zoho"


def _provider() -> ZohoCRMProvider:
    return ProviderFactory.get_crm_provider("zoho")


def get_authorization_url() -> str:
    return zoho_auth.build_authorization_url()


async def handle_oauth_callback(code: str) -> None:
    await zoho_auth.exchange_code_for_token(code)


async def create_contact(data: ContactInput) -> Contact:
    contact = await _provider().create_contact(data)
    repository.upsert_record(
        _PROVIDER, "contact", contact.id, contact.model_dump()
    )
    return contact


async def get_contact(contact_id: str) -> Contact:
    return await _provider().get_contact(contact_id)


async def list_contacts(page: int, per_page: int) -> Page:
    return await _provider().list_contacts(page, per_page)


async def update_contact(contact_id: str, data: ContactInput) -> Contact:
    contact = await _provider().update_contact(contact_id, data)
    repository.upsert_record(
        _PROVIDER, "contact", contact.id, contact.model_dump()
    )
    return contact


async def delete_contact(contact_id: str) -> None:
    await _provider().delete_contact(contact_id)
    repository.mark_deleted(_PROVIDER, "contact", contact_id)


async def create_lead(data: LeadInput) -> Lead:
    lead = await _provider().create_lead(data)
    repository.upsert_record(_PROVIDER, "lead", lead.id, lead.model_dump())
    return lead


async def get_lead(lead_id: str) -> Lead:
    return await _provider().get_lead(lead_id)


async def list_leads(page: int, per_page: int) -> Page:
    return await _provider().list_leads(page, per_page)
