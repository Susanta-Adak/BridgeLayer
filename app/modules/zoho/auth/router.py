from fastapi import APIRouter

from app.core.deps import envelope
from app.core.schemas import AuthUrlResponse
from app.modules.zoho.auth import service

router = APIRouter(prefix="/zoho/auth", tags=["zoho"])


@router.get("/authorize")
async def authorize():
    url = service.build_authorization_url()
    return envelope(AuthUrlResponse(authorization_url=url))


@router.get("/callback")
async def auth_callback(code: str):
    await service.exchange_code_for_token(code)
    return envelope({"authorized": True})
