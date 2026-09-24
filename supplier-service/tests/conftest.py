"""Shared JWT and current-role fixtures for Supplier read endpoints."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app import auth
from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def read_auth(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = uuid4()
    token = jwt.encode(
        {
            "iss": "foc-user-service",
            "aud": "foc-services",
            "exp": datetime.now(UTC) + timedelta(minutes=10),
            "iat": datetime.now(UTC),
            "sub": str(subject),
            "sid": str(uuid4()),
            "roleVersion": 1,
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    class FakeJwks:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=key.public_key())

    decision = {"subjectId": str(subject), "accountStatus": "ACTIVE", "systemRole": "USER", "allowed": False}
    actions = []

    def authorize(_url, *, headers, json, timeout):
        actions.append(json["action"])
        return SimpleNamespace(status_code=200, json=lambda: decision)

    monkeypatch.setattr(auth, "jwks_client", lambda _url: FakeJwks())
    monkeypatch.setattr(auth.httpx, "post", authorize)
    app.dependency_overrides[get_settings] = lambda: Settings(
        database_url="unused-in-http-test",
        user_service_base_url="http://user-service:8000",
        supplier_service_shared_secret="test-service-secret",
        jwt_issuer="foc-user-service",
        jwt_audience="foc-services",
    )
    yield token, decision, actions
    app.dependency_overrides.clear()
