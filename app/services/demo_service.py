"""Facade over the demo/stub provider.

Deliberately identical in shape to zoho_service.py's contact/lead
methods - proof that a third provider slots into the same Facade
pattern with no changes to api/, db/, or the other services.
"""

from app.providers.demo_provider.client import DemoCRMProvider
from app.providers.factory import ProviderFactory
from app.providers.schemas import Contact, ContactInput, Lead, LeadInput, Page


def _provider() -> DemoCRMProvider:
    return ProviderFactory.get_crm_provider("demo")


async def create_contact(data: ContactInput) -> Contact:
    return await _provider().create_contact(data)


async def get_contact(contact_id: str) -> Contact:
    return await _provider().get_contact(contact_id)


async def list_contacts(page: int, per_page: int) -> Page:
    return await _provider().list_contacts(page, per_page)


async def update_contact(contact_id: str, data: ContactInput) -> Contact:
    return await _provider().update_contact(contact_id, data)


async def delete_contact(contact_id: str) -> None:
    await _provider().delete_contact(contact_id)


async def create_lead(data: LeadInput) -> Lead:
    return await _provider().create_lead(data)


async def get_lead(lead_id: str) -> Lead:
    return await _provider().get_lead(lead_id)


async def list_leads(page: int, per_page: int) -> Page:
    return await _provider().list_leads(page, per_page)
