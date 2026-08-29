"""Facade for the Demo/stub CRM's Contacts.

Deliberately the same shape as zoho/contacts/service.py's functions
- proof that a third provider slots into the same per-module
template (in-memory store standing in for an HTTP call, then the
same local-mirror save) with no changes to anything outside this
folder.
"""

import itertools

from app.core.exceptions import NotFoundError
from app.core.schemas import PageMeta
from app.db.session import SessionLocal
from app.modules.demo.contacts.models import DemoContact
from app.modules.demo.contacts.schemas import (
    ContactListResponse,
    ContactRequest,
    ContactResponse,
)

_contacts: dict[str, ContactResponse] = {}
_contact_ids = itertools.count(1)


def _save_local(contact: ContactResponse) -> None:
    with SessionLocal() as db:
        row = (
            db.query(DemoContact)
            .filter(DemoContact.external_id == contact.id)
            .first()
        )
        if row is None:
            row = DemoContact(external_id=contact.id)
            db.add(row)
        row.first_name = contact.first_name
        row.last_name = contact.last_name
        row.email = contact.email
        row.phone = contact.phone
        row.company = contact.company
        row.is_deleted = False
        db.commit()


def _mark_local_deleted(external_id: str) -> None:
    with SessionLocal() as db:
        row = (
            db.query(DemoContact)
            .filter(DemoContact.external_id == external_id)
            .first()
        )
        if row is not None:
            row.is_deleted = True
            db.commit()


async def create_contact(data: ContactRequest) -> ContactResponse:
    contact_id = str(next(_contact_ids))
    contact = ContactResponse(id=contact_id, **data.model_dump())
    _contacts[contact_id] = contact
    _save_local(contact)
    return contact


async def get_contact(contact_id: str) -> ContactResponse:
    try:
        return _contacts[contact_id]
    except KeyError:
        raise NotFoundError(f"Demo contact {contact_id} not found") from None


async def list_contacts(page: int, per_page: int) -> ContactListResponse:
    values = list(_contacts.values())
    start = (page - 1) * per_page
    chunk = values[start : start + per_page]
    return ContactListResponse(
        items=chunk,
        meta=PageMeta(
            page=page,
            per_page=per_page,
            has_more=start + per_page < len(values),
        ),
    )


async def update_contact(
    contact_id: str, data: ContactRequest
) -> ContactResponse:
    if contact_id not in _contacts:
        raise NotFoundError(f"Demo contact {contact_id} not found")
    contact = ContactResponse(id=contact_id, **data.model_dump())
    _contacts[contact_id] = contact
    _save_local(contact)
    return contact


async def delete_contact(contact_id: str) -> None:
    if _contacts.pop(contact_id, None) is None:
        raise NotFoundError(f"Demo contact {contact_id} not found")
    _mark_local_deleted(contact_id)
