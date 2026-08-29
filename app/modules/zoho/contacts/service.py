"""Facade for Zoho Contacts.

Calls the Zoho API via client.py and adapts Zoho's JSON shape
to/from ContactRequest/ContactResponse. Zoho is the source of truth
for contact data - nothing is cached or duplicated locally; the
local DB is reserved for OAuth tokens only (see auth/models.py).
"""

from app.core.exceptions import NotFoundError, ProviderAPIError
from app.core.schemas import PageMeta
from app.modules.zoho import client as zoho_client
from app.modules.zoho.contacts.schemas import (
    ContactListResponse,
    ContactRequest,
    ContactResponse,
)

_LIST_FIELDS = "id,First_Name,Last_Name,Email,Phone,Account_Name"


def _to_zoho_payload(contact: ContactRequest) -> dict:
    return {
        "First_Name": contact.first_name,
        "Last_Name": contact.last_name,
        "Email": contact.email,
        "Phone": contact.phone,
        "Account_Name": contact.company,
    }


def _from_zoho_record(record: dict) -> ContactResponse:
    return ContactResponse(
        id=str(record["id"]),
        first_name=record.get("First_Name"),
        last_name=record.get("Last_Name"),
        email=record.get("Email"),
        phone=record.get("Phone"),
        company=(record.get("Account_Name") or {}).get("name")
        if isinstance(record.get("Account_Name"), dict)
        else record.get("Account_Name"),
    )


def _first_result(response, action: str) -> dict:
    body = response.json()
    results = body.get("data") or []
    if not results or results[0].get("status") != "success":
        raise ProviderAPIError(
            f"Zoho failed to {action}", details={"response": body}
        )
    return results[0]


async def create_contact(data: ContactRequest) -> ContactResponse:
    response = await zoho_client.authenticated_request(
        "POST",
        f"{zoho_client.base_url()}/Contacts",
        json={"data": [_to_zoho_payload(data)]},
    )
    result = _first_result(response, "create contact")
    return await get_contact(result["details"]["id"])


async def get_contact(contact_id: str) -> ContactResponse:
    response = await zoho_client.authenticated_request(
        "GET", f"{zoho_client.base_url()}/Contacts/{contact_id}"
    )
    if response.status_code in (404, 204):
        raise NotFoundError(f"Zoho contact {contact_id} not found")
    if response.status_code != 200:
        raise ProviderAPIError(
            f"Zoho failed to get contact {contact_id}",
            details={
                "status_code": response.status_code,
                "response": response.text,
            },
        )
    data = response.json().get("data") or []
    if not data:
        raise NotFoundError(f"Zoho contact {contact_id} not found")
    return _from_zoho_record(data[0])


async def list_contacts(page: int, per_page: int) -> ContactListResponse:
    response = await zoho_client.authenticated_request(
        "GET",
        f"{zoho_client.base_url()}/Contacts",
        params={
            "page": page,
            "per_page": per_page,
            "fields": _LIST_FIELDS,
        },
    )
    if response.status_code == 204:
        return ContactListResponse(
            items=[],
            meta=PageMeta(page=page, per_page=per_page, has_more=False),
        )
    if response.status_code != 200:
        raise ProviderAPIError(
            "Zoho failed to list contacts",
            details={
                "status_code": response.status_code,
                "response": response.text,
            },
        )
    body = response.json()
    items = [_from_zoho_record(r) for r in body.get("data", [])]
    info = body.get("info", {})
    return ContactListResponse(
        items=items,
        meta=PageMeta(
            page=info.get("page", page),
            per_page=info.get("per_page", per_page),
            has_more=info.get("more_records", False),
        ),
    )


async def update_contact(
    contact_id: str, data: ContactRequest
) -> ContactResponse:
    payload = {"id": contact_id, **_to_zoho_payload(data)}
    response = await zoho_client.authenticated_request(
        "PUT",
        f"{zoho_client.base_url()}/Contacts/{contact_id}",
        json={"data": [payload]},
    )
    _first_result(response, "update contact")
    return await get_contact(contact_id)


async def delete_contact(contact_id: str) -> None:
    response = await zoho_client.authenticated_request(
        "DELETE", f"{zoho_client.base_url()}/Contacts/{contact_id}"
    )
    _first_result(response, "delete contact")
