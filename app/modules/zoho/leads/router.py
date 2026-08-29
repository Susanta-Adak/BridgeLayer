from fastapi import APIRouter, Query

from app.core.deps import envelope
from app.modules.zoho.leads import service
from app.modules.zoho.leads.schemas import LeadRequest

router = APIRouter(prefix="/zoho/leads", tags=["zoho"])


@router.post("", status_code=201)
async def create_lead(payload: LeadRequest):
    lead = await service.create_lead(payload)
    return envelope(lead)


@router.get("/{lead_id}")
async def get_lead(lead_id: str):
    lead = await service.get_lead(lead_id)
    return envelope(lead)


@router.get("")
async def list_leads(
    page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=200)
):
    result = await service.list_leads(page, per_page)
    return envelope(result)
