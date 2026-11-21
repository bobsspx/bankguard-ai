
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.core.security import create_access_token


def make_client(role, *, active=True, session_version=1):
    user = SimpleNamespace(
        id=uuid4(),
        email="synthetic-security@bankguard-demo.com",
        role=role,
        is_active=active,
        session_version=session_version,
    )

    db = MagicMock()

    def scalar(statement):
        sql = str(statement)
        if "staff_users" in sql:
            return user
        return 0

    db.scalar.side_effect = scalar

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=role,
        session_version=1,
    )

    return TestClient(app), token, db


def test_real_jwt_security_analyst_allowed():
    try:
        client, token, _ = make_client("security_analyst")

        with client:
            response = client.get(
                "/api/v1/security/summary",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        assert response.json()["total_login_events"] == 0
    finally:
        app.dependency_overrides.clear()


def test_real_jwt_current_user_returns_valid_email():
    try:
        client, token, _ = make_client("security_analyst")
        with client:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 200
        assert response.json()["email"] == "synthetic-security@bankguard-demo.com"
    finally:
        app.dependency_overrides.clear()


def test_real_jwt_fraud_analyst_denied():
    try:
        client, token, _ = make_client("fraud_analyst")

        with client:
            response = client.get(
                "/api/v1/security/summary",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_real_jwt_inactive_staff_denied():
    try:
        client, token, _ = make_client(
            "security_analyst", active=False
        )

        with client:
            response = client.get(
                "/api/v1/security/summary",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_real_jwt_revoked_session_denied():
    try:
        client, token, _ = make_client(
            "security_analyst", session_version=2
        )

        with client:
            response = client.get(
                "/api/v1/security/summary",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_invalid_bearer_token_denied():
    try:
        client, _, _ = make_client("security_analyst")

        with client:
            response = client.get(
                "/api/v1/security/summary",
                headers={"Authorization": "Bearer invalid.jwt.token"},
            )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
