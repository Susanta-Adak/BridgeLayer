"""Routes for the stub third provider - same shape as routes_zoho.py's

contact/lead endpoints, proving a new provider only needs a thin
router like this one plus a Facade service and a provider class.
"""

from fastapi import APIRouter, Query

from app.api.deps import envelope
from app.api.schemas import (
    ContactListResponse,
    ContactRequest,
    ContactResponse,
    LeadListResponse,
    LeadRequest,
    LeadResponse,
    PageMeta,
)
from app.providers.schemas import ContactInput, LeadInput
from app.services import demo_service

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/contacts", status_code=201)
async def create_contact(payload: ContactRequest):
    contact = await demo_service.create_contact(
        ContactInput(**payload.model_dump())
    )
    return envelope(ContactResponse(**contact.model_dump()))


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str):
    contact = await demo_service.get_contact(contact_id)
    return envelope(ContactResponse(**contact.model_dump()))


@router.get("/contacts")
async def list_contacts(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200)
):
    result = await demo_service.list_contacts(page, per_page)
    return envelope(
        ContactListResponse(
            items=[ContactResponse(**c.model_dump()) for c in result.items],
            meta=PageMeta(
                page=result.page,
                per_page=result.per_page,
                has_more=result.has_more,
            ),
        )
    )


@router.put("/contacts/{contact_id}")
async def update_contact(contact_id: str, payload: ContactRequest):
    contact = await demo_service.update_contact(
        contact_id, ContactInput(**payload.model_dump())
    )
    return envelope(ContactResponse(**contact.model_dump()))


@router.delete("/contacts/{contact_id}", status_code=200)
async def delete_contact(contact_id: str):
    await demo_service.delete_contact(contact_id)
    return envelope({"deleted": True})


@router.post("/leads", status_code=201)
async def create_lead(payload: LeadRequest):
    lead = await demo_service.create_lead(LeadInput(**payload.model_dump()))
    return envelope(LeadResponse(**lead.model_dump()))


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str):
    lead = await demo_service.get_lead(lead_id)
    return envelope(LeadResponse(**lead.model_dump()))


@router.get("/leads")
async def list_leads(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200)
):
    result = await demo_service.list_leads(page, per_page)
    return envelope(
        LeadListResponse(
            items=[LeadResponse(**l.model_dump()) for l in result.items],
            meta=PageMeta(
                page=result.page,
                per_page=result.per_page,
                has_more=result.has_more,
            ),
        )
    )
