"""Adapter: translates Zoho's Leads module JSON shape into

BridgeLayer's unified `Lead` DTO, and vice versa for writes.
"""

from app.core.exceptions import NotFoundError, ProviderAPIError
from app.providers.schemas import Lead, LeadInput, Page


def _to_zoho_payload(lead: LeadInput) -> dict:
    return {
        "First_Name": lead.first_name,
        "Last_Name": lead.last_name,
        "Email": lead.email,
        "Phone": lead.phone,
        "Company": lead.company,
        "Lead_Source": lead.lead_source,
    }


def _from_zoho_record(record: dict) -> Lead:
    return Lead(
        id=str(record["id"]),
        first_name=record.get("First_Name"),
        last_name=record.get("Last_Name"),
        email=record.get("Email"),
        phone=record.get("Phone"),
        company=record.get("Company"),
        lead_source=record.get("Lead_Source"),
    )


_LIST_FIELDS = "id,First_Name,Last_Name,Email,Phone,Company,Lead_Source"


class ZohoLeadsMixin:
    """Mixed into ZohoCRMProvider; assumes self.authenticated_request

    and self.base_url from the sibling client module.
    """

    async def create_lead(self, lead: LeadInput) -> Lead:
        response = await self.authenticated_request(
            "POST",
            f"{self.base_url}/Leads",
            json={"data": [_to_zoho_payload(lead)]},
        )
        result = _first_result(response, "create lead")
        return await self.get_lead(result["details"]["id"])

    async def get_lead(self, lead_id: str) -> Lead:
        response = await self.authenticated_request(
            "GET", f"{self.base_url}/Leads/{lead_id}"
        )
        if response.status_code in (404, 204):
            raise NotFoundError(f"Zoho lead {lead_id} not found")
        if response.status_code != 200:
            raise ProviderAPIError(
                f"Zoho failed to get lead {lead_id}",
                details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
        data = response.json().get("data") or []
        if not data:
            raise NotFoundError(f"Zoho lead {lead_id} not found")
        return _from_zoho_record(data[0])

    async def list_leads(self, page: int, per_page: int) -> Page:
        response = await self.authenticated_request(
            "GET",
            f"{self.base_url}/Leads",
            params={
                "page": page,
                "per_page": per_page,
                "fields": _LIST_FIELDS,
            },
        )
        if response.status_code == 204:
            return Page(items=[], page=page, per_page=per_page, has_more=False)
        if response.status_code != 200:
            raise ProviderAPIError(
                "Zoho failed to list leads",
                details={
                    "status_code": response.status_code,
                    "response": response.text,
                },
            )
        body = response.json()
        items = [_from_zoho_record(r) for r in body.get("data", [])]
        info = body.get("info", {})
        return Page(
            items=items,
            page=info.get("page", page),
            per_page=info.get("per_page", per_page),
            has_more=info.get("more_records", False),
        )


def _first_result(response, action: str) -> dict:
    body = response.json()
    results = body.get("data") or []
    if not results or results[0].get("status") != "success":
        raise ProviderAPIError(
            f"Zoho failed to {action}", details={"response": body}
        )
    return results[0]
