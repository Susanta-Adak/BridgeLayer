import pytest
import respx
from httpx import Response

from app.core.exceptions import ProviderRateLimitError
from app.core.http_client import request_with_retry


@respx.mock
async def test_request_with_retry_recovers_from_transient_500():
    route = respx.get("https://example.test/thing")
    route.side_effect = [Response(500), Response(200, json={"ok": True})]

    response = await request_with_retry(
        "GET", "https://example.test/thing", max_retries=2
    )

    assert response.status_code == 200
    assert route.call_count == 2


@respx.mock
async def test_request_with_retry_raises_rate_limit_after_exhausting_retries():
    respx.get("https://example.test/limited").mock(
        return_value=Response(429, headers={"Retry-After": "0"})
    )

    with pytest.raises(ProviderRateLimitError):
        await request_with_retry(
            "GET", "https://example.test/limited", max_retries=1
        )


@respx.mock
async def test_request_with_retry_returns_non_retryable_error_immediately():
    route = respx.get("https://example.test/bad-request")
    route.mock(return_value=Response(400, json={"error": "bad"}))

    response = await request_with_retry(
        "GET", "https://example.test/bad-request", max_retries=3
    )

    assert response.status_code == 400
    assert route.call_count == 1
