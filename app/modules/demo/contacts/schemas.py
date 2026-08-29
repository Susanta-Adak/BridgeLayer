"""Request/response schemas for /demo/contacts."""

from pydantic import BaseModel, EmailStr

from app.core.schemas import PageMeta


class ContactRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None


class ContactResponse(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None


class ContactListResponse(BaseModel):
    items: list[ContactResponse]
    meta: PageMeta
