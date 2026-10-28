
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_current_staff_user
from app.db.session import get_db
from app.main import app


def make_client(role):
    db = MagicMock()
    db.scalar.side_effect = [20, 5, 2, 1]

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_staff_user] = (
        lambda: SimpleNamespace(role=role)
    )

    return TestClient(app)


def test_security_analyst_can_read_summary():
    try:
        with make_client("security_analyst") as client:
            response = client.get("/api/v1/security/summary")

        assert response.status_code == 200
        assert response.json() == {
            "total_login_events": 20,
            "failed_login_events": 5,
            "security_alerts": 2,
            "open_security_alerts": 1,
        }
    finally:
        app.dependency_overrides.clear()


def test_fraud_analyst_cannot_read_security_summary():
    try:
        with make_client("fraud_analyst") as client:
            response = client.get("/api/v1/security/summary")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_reviewer_cannot_read_security_summary():
    try:
        with make_client("reviewer") as client:
            response = client.get("/api/v1/security/summary")

        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_admin_can_read_security_summary():
    try:
        with make_client("admin") as client:
            response = client.get("/api/v1/security/summary")

        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_request_is_rejected():
    try:
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            response = client.get("/api/v1/security/summary")

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
