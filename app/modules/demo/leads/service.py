"""Facade for the Demo/stub CRM's Leads."""

import itertools

from app.core.exceptions import NotFoundError
from app.core.schemas import PageMeta
from app.db.session import SessionLocal
from app.modules.demo.leads.models import DemoLead
from app.modules.demo.leads.schemas import (
    LeadListResponse,
    LeadRequest,
    LeadResponse,
)

_leads: dict[str, LeadResponse] = {}
_lead_ids = itertools.count(1)


def _save_local(lead: LeadResponse) -> None:
    with SessionLocal() as db:
        row = (
            db.query(DemoLead)
            .filter(DemoLead.external_id == lead.id)
            .first()
        )
        if row is None:
            row = DemoLead(external_id=lead.id)
            db.add(row)
        row.first_name = lead.first_name
        row.last_name = lead.last_name
        row.email = lead.email
        row.phone = lead.phone
        row.company = lead.company
        row.lead_source = lead.lead_source
        db.commit()


async def create_lead(data: LeadRequest) -> LeadResponse:
    lead_id = str(next(_lead_ids))
    lead = LeadResponse(id=lead_id, **data.model_dump())
    _leads[lead_id] = lead
    _save_local(lead)
    return lead


async def get_lead(lead_id: str) -> LeadResponse:
    try:
        return _leads[lead_id]
    except KeyError:
        raise NotFoundError(f"Demo lead {lead_id} not found") from None


async def list_leads(page: int, per_page: int) -> LeadListResponse:
    values = list(_leads.values())
    start = (page - 1) * per_page
    chunk = values[start : start + per_page]
    return LeadListResponse(
        items=chunk,
        meta=PageMeta(
            page=page,
            per_page=per_page,
            has_more=start + per_page < len(values),
        ),
    )
