
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_current_staff_user
from app.db.session import get_db
from datetime import datetime, timezone
from sqlalchemy.dialects import postgresql

def make_client(role="security_analyst"):
    db = MagicMock()
    db.scalar.return_value = 1
    db.execute.return_value.mappings.return_value.all.return_value = []

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_staff_user] = (
        lambda: SimpleNamespace(role=role)
    )

    return TestClient(app), db


def test_security_analyst_can_list_alerts():
    try:
        client, db = make_client()

        with client:
            response = client.get(
                "/api/v1/security/alerts?limit=10&offset=0"
            )

        assert response.status_code == 200
        assert response.json() == {
            "total": 1,
            "limit": 10,
            "offset": 0,
            "items": [],
        }
        db.execute.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_fraud_analyst_cannot_list_security_alerts():
    try:
        client, db = make_client("fraud_analyst")

        with client:
            response = client.get("/api/v1/security/alerts")

        assert response.status_code == 403
        db.execute.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_invalid_pagination_rejected():
    try:
        client, _ = make_client()

        with client:
            response = client.get(
                "/api/v1/security/alerts?limit=101"
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_invalid_status_rejected():
    try:
        client, _ = make_client()

        with client:
            response = client.get(
                "/api/v1/security/alerts?status=invalid"
            )

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_request_rejected():
    try:
        app.dependency_overrides.clear()

        with TestClient(app) as client:
            response = client.get("/api/v1/security/alerts")

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_security_alert_list_excludes_evidence():
    try:
        client, db = make_client()

        alert_id = UUID(int=100)
        event_id = UUID(int=5)

        evidence = {
            "evidence_version": "security-evidence-v1",
            "rule_code": "FAILED_LOGIN_BURST",
            "triggering_event_id": str(event_id),
            "evidence_event_ids": [
                str(UUID(int=i)) for i in range(1, 6)
            ],
            "event_count": 5,
        }

        row = {
            "id": alert_id,
            "login_event_id": event_id,
            "alert_type": "FAILED_LOGIN_BURST",
            "severity": "high",
            "status": "open",
            "title": "Multiple failed login attempts",
            "description": "Synthetic security event",
            "created_at": datetime(
                2026, 10, 25, 12, 0,
                tzinfo=timezone.utc,
            ),
            "evidence": evidence,
        }

        db.execute.return_value.mappings.return_value.all.return_value = [
            row
        ]

        with client:
            response = client.get(
                "/api/v1/security/alerts?limit=10"
            )

        assert response.status_code == 200

        data = response.json()

        assert data["total"] == 1
        assert len(data["items"]) == 1

        item = data["items"][0]

        assert item["id"] == str(alert_id)
        assert item["alert_type"] == "FAILED_LOGIN_BURST"
        
        assert "evidence" not in item
        assert item["id"] == str(alert_id)
        assert item["alert_type"] == "FAILED_LOGIN_BURST"


    finally:
        app.dependency_overrides.clear()


def test_security_alert_list_uses_pagination_in_sql():
    try:
        client, db = make_client()

        with client:
            response = client.get(
                "/api/v1/security/alerts"
                "?limit=10&offset=5&status=open"
            )

        assert response.status_code == 200

        statement = db.execute.call_args.args[0]

        compiled = statement.compile(
            dialect=postgresql.dialect()
        )

        sql = str(compiled).lower()

        assert "limit" in sql
        assert "offset" in sql
        assert "order by" in sql
        assert "security_alert_evidence" not in sql
        assert "login_event_id is not null" in sql

        values = list(compiled.params.values())

        assert 10 in values
        assert 5 in values
        assert "open" in values

    finally:
        app.dependency_overrides.clear()


def test_alert_list_does_not_select_evidence_table():
    try:
        client, db = make_client()

        with client:
            response = client.get(
                "/api/v1/security/alerts"
            )

        assert response.status_code == 200

        statement = db.execute.call_args.args[0]

        table_names = {
            table.name
            for table in statement.get_final_froms()
        }

        assert table_names == {"alerts"}

        selected = {
            column.key
            for column in statement.selected_columns
        }

        assert "snapshot" not in selected
        assert "ip_address" not in selected

    finally:
        app.dependency_overrides.clear()
