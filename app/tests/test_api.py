"""API-level tests through TestClient: envelope shape, validation

errors, and a full contact lifecycle routed through the actual
FastAPI endpoints (not called as plain functions) - the external
Zoho call is mocked with respx, everything above that is real.
"""

import pytest
import respx
from httpx import Response

from app.core.config import get_settings
from app.modules.zoho.auth import service as zoho_auth


@pytest.fixture(autouse=True)
def _seed_zoho_token():
    zoho_auth._save_token(
        {
            "access_token": "seeded-access-token",
            "refresh_token": "seeded-refresh-token",
            "expires_in": 3600,
        },
        require_refresh_token=True,
    )


def _crm_base():
    settings = get_settings()
    return f"{settings.zoho_api_base_url}/crm/v3"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok"},
        "error": None,
    }


def test_zoho_authorize_returns_url(client):
    response = client.get("/api/v1/zoho/auth/authorize")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "authorization_url" in body["data"]


def test_zoho_contact_missing_fields_returns_validation_error(client):
    response = client.post(
        "/api/v1/zoho/contacts", json={"first_name": "Ada"}
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"


def test_zoho_contact_invalid_email_returns_validation_error(client):
    response = client.post(
        "/api/v1/zoho/contacts",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@respx.mock
def test_zoho_contact_lifecycle_through_api(client):
    base = _crm_base()
    respx.post(f"{base}/Contacts").mock(
        return_value=Response(
            201,
            json={
                "data": [
                    {
                        "code": "SUCCESS",
                        "status": "success",
                        "details": {"id": "701"},
                    }
                ]
            },
        )
    )
    respx.get(f"{base}/Contacts/701").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "701",
                        "First_Name": "Ada",
                        "Last_Name": "Lovelace",
                        "Email": "ada@example.com",
                    }
                ]
            },
        )
    )

    create_resp = client.post(
        "/api/v1/zoho/contacts",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
        },
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["success"] is True
    assert body["data"]["id"] == "701"

    respx.get(f"{base}/Contacts").mock(
        return_value=Response(
            200,
            json={
                "data": [
                    {
                        "id": "701",
                        "First_Name": "Ada",
                        "Last_Name": "Lovelace",
                        "Email": "ada@example.com",
                    }
                ],
                "info": {"page": 1, "per_page": 20, "more_records": False},
            },
        )
    )
    list_resp = client.get("/api/v1/zoho/contacts")
    assert list_resp.status_code == 200
    assert list_resp.json()["success"] is True
    assert "meta" in list_resp.json()["data"]

    respx.get(f"{base}/Contacts/999").mock(
        return_value=Response(200, json={"data": []})
    )
    missing_resp = client.get("/api/v1/zoho/contacts/999")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["success"] is False
    assert missing_resp.json()["error"]["code"] == "not_found"
