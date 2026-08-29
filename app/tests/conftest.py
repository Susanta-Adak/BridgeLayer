"""Test env vars must be set before any `app.*` module is imported,

since `get_settings()` is cached on first call. All external HTTP
calls are mocked with respx - no test ever touches a real Zoho or
Shopify endpoint.
"""

import os
import tempfile

_tmp_dir = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_dir}/test.db"
os.environ["ZOHO_CLIENT_ID"] = "test-client-id"
os.environ["ZOHO_CLIENT_SECRET"] = "test-client-secret"
os.environ["ZOHO_REDIRECT_URI"] = "http://localhost:8000/zoho/auth/callback"
os.environ["ZOHO_ACCOUNTS_BASE_URL"] = "https://accounts.zoho.test"
os.environ["ZOHO_API_BASE_URL"] = "https://api.zoho.test"
os.environ["SHOPIFY_SHOP_DOMAIN"] = "test-shop.myshopify.com"
os.environ["SHOPIFY_ACCESS_TOKEN"] = "test-shopify-token"
os.environ["SHOPIFY_API_VERSION"] = "2024-07"
os.environ["SHOPIFY_CLIENT_ID"] = "test-shopify-client-id"
os.environ["SHOPIFY_CLIENT_SECRET"] = "test-shopify-client-secret"
os.environ["SHOPIFY_REDIRECT_URI"] = (
    "http://localhost:8000/shopify/auth/callback"
)
os.environ["HTTP_BACKOFF_BASE_SECONDS"] = "0.01"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.database import init_db  # noqa: E402

get_settings.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    init_db()
    yield


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
