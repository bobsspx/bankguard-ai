
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_current_staff_user
from app.db.session import get_db


ALERT_ID = UUID(int=100)
URL = f"/api/v1/security/alerts/{ALERT_ID}/evidence"


def make_client(role, record=None):
    db = MagicMock()
    db.execute.return_value.mappings.return_value.one_or_none.return_value = record

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_staff_user] = (
        lambda: SimpleNamespace(role=role)
    )
    return TestClient(app), db


def test_security_analyst_reads_evidence():
    record = {
        "alert_id": ALERT_ID,
        "alert_type": "FAILED_LOGIN_BURST",
        "evidence": {
            "evidence_version": "security-evidence-v1",
            "event_count": 5,
            "evidence_event_ids": [
                str(UUID(int=i)) for i in range(1, 6)
            ],
        },
    }
    try:
        client, db = make_client("security_analyst", record)
        with client:
            response = client.get(URL)

        assert response.status_code == 200
        assert response.json()["evidence"]["event_count"] == 5
        db.execute.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_fraud_analyst_is_denied():
    try:
        client, db = make_client("fraud_analyst")
        with client:
            response = client.get(URL)
        assert response.status_code == 403
        db.execute.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_missing_evidence_returns_404():
    try:
        client, _ = make_client("security_analyst")
        with client:
            response = client.get(URL)
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_is_denied():
    try:
        app.dependency_overrides.clear()
        with TestClient(app) as client:
            response = client.get(URL)
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_invalid_uuid_returns_422():
    try:
        client, _ = make_client("security_analyst")
        with client:
            response = client.get(
                "/api/v1/security/alerts/not-a-uuid/evidence"
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
