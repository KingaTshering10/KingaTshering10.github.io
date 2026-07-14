import os
import uuid

# Environment must be configured before any app import.
os.environ.setdefault("DRUK_ENVIRONMENT", "test")
os.environ.setdefault("DRUK_DATABASE_URL", f"sqlite:///./var/test-{uuid.uuid4().hex}.db")
os.environ.setdefault("DRUK_JWT_SECRET", "test-secret-not-for-production")

import pytest
from fastapi.testclient import TestClient

from app.core.ratelimit import rate_limiter
from app.db.base import Base
from app.db.session import get_engine
from app.main import app
from app.services.notifications import mock_email, mock_push, mock_sms

os.makedirs("var", exist_ok=True)


@pytest.fixture(scope="session")
def client() -> TestClient:
    Base.metadata.create_all(get_engine())
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clean_state():
    rate_limiter.reset()
    mock_email.outbox.clear()
    mock_sms.outbox.clear()
    mock_push.outbox.clear()
    yield


def register_user(client: TestClient, role: str, email: str | None = None, **kwargs) -> dict:
    email = email or f"{role}-{uuid.uuid4().hex[:10]}@example.bt"
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Str0ngPassw0rd", "role": role, **kwargs},
    )
    assert resp.status_code == 201, resp.text
    return {"email": email, "password": "Str0ngPassw0rd", **resp.json()}


def login(client: TestClient, email: str, password: str = "Str0ngPassw0rd") -> dict:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_headers(client: TestClient, email: str, password: str = "Str0ngPassw0rd") -> dict:
    tokens = login(client, email, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def create_admin(client: TestClient) -> dict:
    """Admins cannot self-register; insert directly like the seed script does."""
    from app.core.security import hash_password
    from app.db.session import get_sessionmaker
    from app.models import User

    email = f"admin-{uuid.uuid4().hex[:10]}@drukagrilink.bt"
    with get_sessionmaker()() as db:
        user = User(
            email=email,
            password_hash=hash_password("Str0ngPassw0rd"),
            role="admin",
            is_verified=True,
        )
        db.add(user)
        db.commit()
    return {"email": email, "password": "Str0ngPassw0rd"}


@pytest.fixture()
def admin_headers(client):
    admin = create_admin(client)
    return auth_headers(client, admin["email"])


@pytest.fixture()
def make_user(client):
    """Factory: returns (user_dict, headers) for a fresh user of the given role."""

    def _make(role: str, **kwargs):
        user = register_user(client, role, **kwargs)
        return user, auth_headers(client, user["email"])

    return _make
