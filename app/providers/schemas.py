"""Unified internal DTOs.

Every provider's Adapter code (e.g. zoho/contacts.py,
shopify/customers.py) translates its own raw JSON shape into these
schemas before returning to the service layer. Nothing above the
provider layer ever sees a Zoho or Shopify-shaped payload.
"""

from pydantic import BaseModel


class Contact(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None


class ContactInput(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    company: str | None = None


class Lead(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    lead_source: str | None = None


class LeadInput(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    company: str | None = None
    lead_source: str | None = None


class Customer(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None


class CustomerInput(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str | None = None


class Order(BaseModel):
    order_id: str
    customer: Customer | None = None
    total_price: str
    currency: str
    order_status: str
    created_at: str


class Page(BaseModel):
    """Generic pagination wrapper returned by list_* provider methods."""

    items: list
    page: int
    per_page: int
    has_more: bool
