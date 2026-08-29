"""Minimal webhook receiver (bonus). Verifies Shopify's HMAC

signature when a webhook secret is configured, then logs the event.
There's no subscription/queueing here - just proof the surface area
exists and is verified correctly, which is the scoped bonus ask.
"""

import base64
import hashlib
import hmac
import logging

from fastapi import APIRouter, Header, Request

from app.core.config import get_settings
from app.core.deps import envelope
from app.core.exceptions import ProviderAuthError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/shopify")
async def shopify_webhook(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_topic: str | None = Header(default=None),
):
    settings = get_settings()
    body = await request.body()

    if settings.shopify_webhook_secret:
        digest = hmac.new(
            settings.shopify_webhook_secret.encode(), body, hashlib.sha256
        ).digest()
        expected = base64.b64encode(digest).decode()
        if not x_shopify_hmac_sha256 or not hmac.compare_digest(
            expected, x_shopify_hmac_sha256
        ):
            raise ProviderAuthError("Invalid Shopify webhook signature")

    logger.info("Received Shopify webhook topic=%s", x_shopify_topic)
    return envelope({"received": True, "topic": x_shopify_topic})
