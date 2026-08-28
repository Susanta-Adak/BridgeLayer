"""Shared async HTTP client (Singleton) with retry-with-backoff and

rate-limit awareness. Every provider sends requests through the same
connection-pooled client instead of creating a new one per call.
"""

import asyncio
import logging

import httpx

from app.core.config import get_settings
from app.core.exceptions import ProviderRateLimitError, ProviderTimeoutError

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_http_client() -> httpx.AsyncClient:
    """Return the process-wide shared AsyncClient, creating it lazily."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)
    return _client


async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int | None = None,
    **kwargs,
) -> httpx.Response:
    """Send a request, retrying transient failures with exponential

    backoff. Honors a provider's `Retry-After` header when present
    (typically on 429 rate-limit responses).
    """
    settings = get_settings()
    retries = (
        max_retries if max_retries is not None else settings.http_max_retries
    )
    client = get_http_client()

    attempt = 0
    while True:
        response: httpx.Response | None = None
        try:
            response = await client.request(method, url, **kwargs)
        except httpx.TimeoutException as exc:
            if attempt >= retries:
                raise ProviderTimeoutError(
                    f"Timed out calling {url} after {attempt + 1} attempts"
                ) from exc
        else:
            if response.status_code not in _RETRYABLE_STATUS_CODES:
                return response
            if attempt >= retries:
                if response.status_code == 429:
                    raise ProviderRateLimitError(
                        f"Rate limited by {url} after {attempt + 1} attempts",
                        details={"status_code": response.status_code},
                    )
                return response

        delay = _backoff_delay(attempt, settings.http_backoff_base_seconds)
        if response is not None:
            delay = _retry_after_override(response, delay)
        logger.warning(
            "Retrying %s %s (attempt %s/%s) in %.2fs",
            method,
            url,
            attempt + 1,
            retries,
            delay,
        )
        await asyncio.sleep(delay)
        attempt += 1


def _backoff_delay(attempt: int, base: float) -> float:
    return base * (2**attempt)


def _retry_after_override(response: httpx.Response, default: float) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return default
    try:
        return float(retry_after)
    except ValueError:
        return default
