"""Generic HTTP-layer schemas shared by every module: the response

envelope, pagination metadata, and the OAuth-URL response shape.
Provider-specific request/response schemas (ContactRequest, and so
on) live in each module's own schemas.py, not here - this file only
holds shapes with no Zoho/Shopify-specific meaning.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

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


class AuthUrlResponse(BaseModel):
    authorization_url: str
