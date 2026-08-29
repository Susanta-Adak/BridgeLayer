from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.core.deps import envelope
from app.core.exceptions import ValidationError
from app.core.schemas import AuthUrlResponse
from app.modules.shopify.auth import service

router = APIRouter(prefix="/shopify/auth", tags=["shopify"])


@router.get("/authorize")
async def authorize():
    url = service.build_authorization_url()
    return envelope(AuthUrlResponse(authorization_url=url))


@router.get("/authorize/redirect")
async def authorize_redirect():
    """Convenience endpoint: redirect the browser straight to Shopify."""
    return RedirectResponse(service.build_authorization_url())


@router.get("/callback")
async def auth_callback(request: Request):
    """Shopify signs every query param it sends (which can include

    extras like `host` depending on app type), so the HMAC has to be
    verified over whatever was actually sent - not a hardcoded
    subset of fields.
    """
    params = dict(request.query_params)
    hmac_signature = params.pop("hmac", None)
    params.pop("signature", None)
    if not hmac_signature:
        raise ValidationError("Missing hmac query parameter")

    await service.handle_callback(
        params=params, hmac_signature=hmac_signature
    )
    return envelope({"authorized": True})
