from fastapi import APIRouter, Query

from app.core.deps import envelope
from app.modules.demo.contacts import service
from app.modules.demo.contacts.schemas import ContactRequest

router = APIRouter(prefix="/demo/contacts", tags=["demo"])


@router.post("", status_code=201)
async def create_contact(payload: ContactRequest):
    contact = await service.create_contact(payload)
    return envelope(contact)


@router.get("/{contact_id}")
async def get_contact(contact_id: str):
    contact = await service.get_contact(contact_id)
    return envelope(contact)


@router.get("")
async def list_contacts(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200)
):
    result = await service.list_contacts(page, per_page)
    return envelope(result)


@router.put("/{contact_id}")
async def update_contact(contact_id: str, payload: ContactRequest):
    contact = await service.update_contact(contact_id, payload)
    return envelope(contact)


@router.delete("/{contact_id}", status_code=200)
async def delete_contact(contact_id: str):
    await service.delete_contact(contact_id)
    return envelope({"deleted": True})
