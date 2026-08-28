"""Adapter: translates Zoho's Contacts module JSON shape into

BridgeLayer's unified `Contact` DTO, and vice versa for writes.
"""

from app.core.exceptions import NotFoundError, ProviderAPIError
from app.providers.schemas import Contact, ContactInput, Page


def _to_zoho_payload(contact: ContactInput) -> dict:
    return {
        "First_Name": contact.first_name,
        "Last_Name": contact.last_name,
        "Email": contact.email,
        "Phone": contact.phone,
        "Account_Name": contact.company,
    }


def _from_zoho_record(record: dict) -> Contact:
    return Contact(
        id=str(record["id"]),
        first_name=record.get("First_Name"),
        last_name=record.get("Last_Name"),
        email=record.get("Email"),
        phone=record.get("Phone"),
        company=(record.get("Account_Name") or {}).get("name")
        if isinstance(record.get("Account_Name"), dict)
        else record.get("Account_Name"),
    )


class ZohoContactsMixin:
    """Mixed into ZohoCRMProvider; assumes self.authenticated_request

    and self.base_url from the sibling client module.
    """

    async def create_contact(self, contact: ContactInput) -> Contact:
        response = await self.authenticated_request(
            "POST",
            f"{self.base_url}/Contacts",
            json={"data": [_to_zoho_payload(contact)]},
        )
        result = _first_result(response, "create contact")
        return await self.get_contact(result["details"]["id"])

    async def get_contact(self, contact_id: str) -> Contact:
        response = await self.authenticated_request(
            "GET", f"{self.base_url}/Contacts/{contact_id}"
        )
        if response.status_code == 404:
            raise NotFoundError(f"Zoho contact {contact_id} not found")
        data = response.json().get("data") or []
        if not data:
            raise NotFoundError(f"Zoho contact {contact_id} not found")
        return _from_zoho_record(data[0])

    async def list_contacts(self, page: int, per_page: int) -> Page:
        response = await self.authenticated_request(
            "GET",
            f"{self.base_url}/Contacts",
            params={"page": page, "per_page": per_page},
        )
        if response.status_code == 204:
            return Page(items=[], page=page, per_page=per_page, has_more=False)
        body = response.json()
        items = [_from_zoho_record(r) for r in body.get("data", [])]
        info = body.get("info", {})
        return Page(
            items=items,
            page=info.get("page", page),
            per_page=info.get("per_page", per_page),
            has_more=info.get("more_records", False),
        )

    async def update_contact(
        self, contact_id: str, contact: ContactInput
    ) -> Contact:
        payload = {"id": contact_id, **_to_zoho_payload(contact)}
        response = await self.authenticated_request(
            "PUT",
            f"{self.base_url}/Contacts/{contact_id}",
            json={"data": [payload]},
        )
        _first_result(response, "update contact")
        return await self.get_contact(contact_id)

    async def delete_contact(self, contact_id: str) -> None:
        response = await self.authenticated_request(
            "DELETE", f"{self.base_url}/Contacts/{contact_id}"
        )
        _first_result(response, "delete contact")


def _first_result(response, action: str) -> dict:
    body = response.json()
    results = body.get("data") or []
    if not results or results[0].get("status") != "success":
        raise ProviderAPIError(
            f"Zoho failed to {action}", details={"response": body}
        )
    return results[0]
