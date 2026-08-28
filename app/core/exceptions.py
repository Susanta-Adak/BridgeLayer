"""Typed exceptions shared across all providers and services.

Provider code should only ever raise these (never let raw httpx or
SDK exceptions bubble up) so the API layer can map them to a single
consistent error envelope without knowing anything about Zoho or
Shopify.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class BridgeLayerError(Exception):
    """Base class for all application errors."""

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(BridgeLayerError):
    """Raised when input fails validation before an external call."""

    http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    error_code = "validation_error"


class NotFoundError(BridgeLayerError):
    """Raised when a requested resource does not exist."""

    http_status = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ProviderError(BridgeLayerError):
    """Base class for errors originating from a third-party provider."""

    http_status = status.HTTP_502_BAD_GATEWAY
    error_code = "provider_error"


class ProviderAuthError(ProviderError):
    """Authentication/authorization failed against the provider."""

    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "provider_auth_error"


class ProviderAPIError(ProviderError):
    """The provider returned an error response for a valid request."""

    http_status = status.HTTP_502_BAD_GATEWAY
    error_code = "provider_api_error"


class ProviderRateLimitError(ProviderError):
    """The provider rejected the request due to rate limiting."""

    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "provider_rate_limited"


class ProviderTimeoutError(ProviderError):
    """The provider did not respond within the configured timeout."""

    http_status = status.HTTP_504_GATEWAY_TIMEOUT
    error_code = "provider_timeout"


class ProviderNotFoundError(ProviderError):
    """Unknown provider name requested from the factory."""

    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "unknown_provider"


def _error_envelope(code: str, message: str, details: dict) -> dict:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "details": details},
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Map every BridgeLayerError (and validation errors) to the

    `{success, data, error}` envelope instead of letting FastAPI's
    default handlers leak raw tracebacks or provider payloads.
    """

    @app.exception_handler(BridgeLayerError)
    async def handle_bridgelayer_error(
        request: Request, exc: BridgeLayerError
    ) -> JSONResponse:
        logger.warning("%s: %s", exc.error_code, exc.message)
        return JSONResponse(
            status_code=exc.http_status,
            content=_error_envelope(exc.error_code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_envelope(
                "validation_error",
                "Request validation failed",
                {"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_envelope(
                "internal_error", "An unexpected error occurred", {}
            ),
        )
