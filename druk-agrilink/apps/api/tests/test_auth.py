from tests.conftest import auth_headers, login, register_user


def test_register_and_login(client):
    user = register_user(client, "farmer")
    assert user["role"] == "farmer"
    assert user["is_verified"] is False
    tokens = login(client, user["email"])
    assert tokens["access_token"] and tokens["refresh_token"]


def test_register_duplicate_email_conflict(client):
    user = register_user(client, "farmer")
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": user["email"], "password": "Str0ngPassw0rd", "role": "farmer"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_TAKEN"


def test_register_admin_forbidden(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "evil@example.bt", "password": "Str0ngPassw0rd", "role": "admin"},
    )
    assert resp.status_code == 422


def test_weak_password_rejected(client):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.bt", "password": "short", "role": "farmer"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] in ("PASSWORD_POLICY", "VALIDATION_FAILED")


def test_login_wrong_password(client):
    user = register_user(client, "farmer")
    resp = client.post("/api/v1/auth/login", json={"email": user["email"], "password": "WrongPass123"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_requires_auth(client):
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_me_returns_profile(client):
    user = register_user(client, "buyer")
    headers = auth_headers(client, user["email"])
    resp = client.get("/api/v1/users/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == user["email"]


def test_refresh_rotation_and_reuse_detection(client):
    user = register_user(client, "farmer")
    tokens = login(client, user["email"])
    first_refresh = tokens["refresh_token"]

    # rotate once
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert resp.status_code == 200
    second_refresh = resp.json()["refresh_token"]
    assert second_refresh != first_refresh

    # reusing the rotated token must fail and revoke the family
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "REFRESH_REUSED"

    # the newer token (same family) is also revoked
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh})
    assert resp.status_code == 401


def test_login_rate_limited_per_account(client):
    user = register_user(client, "farmer")
    last = None
    for _ in range(12):
        last = client.post("/api/v1/auth/login", json={"email": user["email"], "password": "WrongPass123"})
    assert last is not None and last.status_code == 429


def test_registration_notification_created(client):
    from app.services.notifications import mock_email

    register_user(client, "farmer")
    assert any(d.subject == "Registration received" for d in mock_email.outbox)


def test_error_envelope_has_request_id(client):
    resp = client.post("/api/v1/auth/login", json={"email": "nobody@example.bt", "password": "Xx12345678"})
    body = resp.json()
    assert body["error"]["request_id"]
    assert resp.headers.get("X-Request-ID")
