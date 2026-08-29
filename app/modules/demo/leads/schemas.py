"""Request/response schemas for /demo/leads."""

from pydantic import BaseModel, EmailStr

from app.core.schemas import PageMeta


class LeadRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    lead_source: str | None = None


class LeadResponse(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    lead_source: str | None = None


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    meta: PageMeta
