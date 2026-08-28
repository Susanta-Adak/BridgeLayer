from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.api.deps import envelope
from app.api.schemas import (
    AuthUrlResponse,
    ContactListResponse,
    ContactRequest,
    ContactResponse,
    LeadListResponse,
    LeadRequest,
    LeadResponse,
    PageMeta,
)
from app.providers.schemas import ContactInput, LeadInput
from app.services import zoho_service

router = APIRouter(prefix="/zoho", tags=["zoho"])


@router.get("/auth/authorize")
async def authorize():
    url = zoho_service.get_authorization_url()
    return envelope(AuthUrlResponse(authorization_url=url))


@router.get("/auth/authorize/redirect")
async def authorize_redirect():
    """Convenience endpoint: redirect the browser straight to Zoho."""
    return RedirectResponse(zoho_service.get_authorization_url())


@router.get("/auth/callback")
async def auth_callback(code: str):
    await zoho_service.handle_oauth_callback(code)
    return envelope({"authorized": True})


@router.post("/contacts", status_code=201)
async def create_contact(payload: ContactRequest):
    contact = await zoho_service.create_contact(
        ContactInput(**payload.model_dump())
    )
    return envelope(ContactResponse(**contact.model_dump()))


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str):
    contact = await zoho_service.get_contact(contact_id)
    return envelope(ContactResponse(**contact.model_dump()))


@router.get("/contacts")
async def list_contacts(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200)
):
    result = await zoho_service.list_contacts(page, per_page)
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
    contact = await zoho_service.update_contact(
        contact_id, ContactInput(**payload.model_dump())
    )
    return envelope(ContactResponse(**contact.model_dump()))


@router.delete("/contacts/{contact_id}", status_code=200)
async def delete_contact(contact_id: str):
    await zoho_service.delete_contact(contact_id)
    return envelope({"deleted": True})


@router.post("/leads", status_code=201)
async def create_lead(payload: LeadRequest):
    lead = await zoho_service.create_lead(LeadInput(**payload.model_dump()))
    return envelope(LeadResponse(**lead.model_dump()))


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str):
    lead = await zoho_service.get_lead(lead_id)
    return envelope(LeadResponse(**lead.model_dump()))


@router.get("/leads")
async def list_leads(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200)
):
    result = await zoho_service.list_leads(page, per_page)
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
