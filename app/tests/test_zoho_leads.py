"""Exercises app.modules.zoho.leads.service end to end (mocked Zoho

HTTP calls via respx). Zoho is the source of truth for lead data.
"""

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.modules.zoho.auth import service as zoho_auth
from app.modules.zoho.leads import service as leads_service
from app.modules.zoho.leads.schemas import LeadRequest


@pytest.fixture(autouse=True)
def _seed_token():
    zoho_auth._save_token(
        {
            "access_token": "seeded-access-token",
            "refresh_token": "seeded-refresh-token",
            "expires_in": 3600,
        },
        require_refresh_token=True,
    )


def _crm_base():
    settings = get_settings()
    return f"{settings.zoho_api_base_url}/crm/v3"


@respx.mock
async def test_create_lead_creates_then_fetches_record():
    base = _crm_base()
    respx.post(f"{base}/Leads").mock(
        return_value=Response(
            201,
            json={
                "data": [
                    {
                        "code": "SUCCESS",
                        "status": "success",
                        "details": {"id": "222"},
                    }
                ]
            },
        )
    )
    respx.get(f"{base}/Leads/222").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "222",
                        "First_Name": "Grace",
                        "Last_Name": "Hopper",
                        "Email": "grace@example.com",
                        "Company": "Navy",
                        "Lead_Source": "Web",
                    }
                ]
            },
        )
    )

    lead = await leads_service.create_lead(
        LeadRequest(
            first_name="Grace",
            last_name="Hopper",
            email="grace@example.com",
            company="Navy",
            lead_source="Web",
        )
    )

    assert lead.id == "222"
    assert lead.lead_source == "Web"


@respx.mock
async def test_list_leads_maps_pagination_info():
    base = _crm_base()
    respx.get(f"{base}/Leads").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "1",
                        "First_Name": "Grace",
                        "Last_Name": "Hopper",
                        "Email": "grace@example.com",
                    }
                ],
                "info": {"page": 1, "per_page": 20, "more_records": False},
            },
        )
    )

    page = await leads_service.list_leads(1, 20)

    assert len(page.items) == 1
    assert page.meta.has_more is False
