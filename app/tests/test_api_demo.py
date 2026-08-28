def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok"},
        "error": None,
    }


def test_demo_contact_lifecycle(client):
    create_resp = client.post(
        "/demo/contacts",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
        },
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["success"] is True
    contact_id = body["data"]["id"]

    get_resp = client.get(f"/demo/contacts/{contact_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["email"] == "ada@example.com"

    update_resp = client.put(
        f"/demo/contacts/{contact_id}",
        json={
            "first_name": "Ada",
            "last_name": "Byron",
            "email": "ada@example.com",
        },
    )
    assert update_resp.json()["data"]["last_name"] == "Byron"

    list_resp = client.get("/demo/contacts")
    assert list_resp.status_code == 200
    assert list_resp.json()["success"] is True
    assert "meta" in list_resp.json()["data"]

    delete_resp = client.delete(f"/demo/contacts/{contact_id}")
    assert delete_resp.json()["data"]["deleted"] is True

    missing_resp = client.get(f"/demo/contacts/{contact_id}")
    assert missing_resp.status_code == 404
    assert missing_resp.json()["success"] is False
    assert missing_resp.json()["error"]["code"] == "not_found"


def test_demo_contact_missing_fields_returns_validation_error(client):
    response = client.post("/demo/contacts", json={"first_name": "Ada"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"


def test_demo_contact_invalid_email_returns_validation_error(client):
    response = client.post(
        "/demo/contacts",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "not-an-email",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_demo_lead_lifecycle(client):
    create_resp = client.post(
        "/demo/leads",
        json={
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "grace@example.com",
            "lead_source": "Web",
        },
    )
    assert create_resp.status_code == 201
    lead_id = create_resp.json()["data"]["id"]

    get_resp = client.get(f"/demo/leads/{lead_id}")
    assert get_resp.json()["data"]["lead_source"] == "Web"

    list_resp = client.get("/demo/leads")
    assert list_resp.json()["success"] is True


def test_zoho_authorize_returns_url(client):
    response = client.get("/zoho/auth/authorize")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "authorization_url" in body["data"]
