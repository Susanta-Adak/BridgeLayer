"""Request/response schemas for /shopify/customers."""

from pydantic import BaseModel, EmailStr

from app.core.schemas import PageMeta


class CustomerRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None = None


class CustomerResponse(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    meta: PageMeta
