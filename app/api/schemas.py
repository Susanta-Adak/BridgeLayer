"""Request/response schemas for the HTTP layer, plus the single

response envelope every endpoint returns: `{success, data, error}`.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, EmailStr

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict = {}


class Envelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: ErrorDetail | None = None


class PageMeta(BaseModel):
    page: int
    per_page: int
    has_more: bool


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


class OrderResponse(BaseModel):
    order_id: str
    customer: CustomerResponse | None = None
    total_price: str
    currency: str
    order_status: str
    created_at: str


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    meta: PageMeta


class AuthUrlResponse(BaseModel):
    authorization_url: str
