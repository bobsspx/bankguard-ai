from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from app.api.dependencies import get_current_staff_user
from app.db.session import get_db
from app.models.alert import Alert

ID = UUID(int=400)
URL = f"/api/v1/security/alerts/{ID}"


@pytest.fixture
def harness():
    db = MagicMock()
    alert = Alert(id=ID, login_event_id=UUID(int=2), alert_type="NEW_DEVICE_LOGIN",
        severity="medium", status="open", title="New device", description="Synthetic",
        created_at=datetime.now(timezone.utc), resolved_at=None)
    db.scalar.return_value = alert
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role="security_analyst", email="synthetic@test.invalid")
    with TestClient(app) as client:
        yield client, db, alert
    app.dependency_overrides.clear()


def payload(**changes):
    return dict(status="investigating", expected_status="open", reason="Review event evidence", **changes)


def test_transition_commits_audit_and_status_together(harness):
    client, db, alert = harness
    response = client.patch(URL, json=payload())
    assert response.status_code == 200
    assert response.json()["status"] == alert.status == "investigating"
    audit = db.add.call_args.args[0]
    assert audit.details["previous_status"] == "open"
    assert audit.details["reason"] == "Review event evidence"
    assert "FOR UPDATE" in str(db.scalar.call_args.args[0])
    db.commit.assert_called_once()


@pytest.mark.parametrize("role", ["fraud_analyst", "reviewer"])
def test_cannot_triage_without_security_monitor_permission(harness, role):
    client, db, _ = harness
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role=role)
    assert client.patch(URL, json=payload()).status_code == 403
    db.scalar.assert_not_called()
    db.commit.assert_not_called()


def test_missing_alert_is_404_and_query_excludes_non_security_alerts(harness):
    client, db, _ = harness
    db.scalar.return_value = None
    assert client.get(URL).status_code == 404
    sql = str(db.scalar.call_args.args[0])
    assert "login_event_id IS NOT NULL" in sql and "alert_type IN" in sql


@pytest.mark.parametrize("change", [{"reason": "   "}, {"status": "open"}, {"expected_status": "unknown"}])
def test_invalid_triage_input_never_queries_database(harness, change):
    client, db, _ = harness
    data = payload()
    data.update(change)
    assert client.patch(URL, json=data).status_code == 422
    db.scalar.assert_not_called()


def test_stale_expected_status_is_409(harness):
    client, db, alert = harness
    alert.status = "resolved"
    assert client.patch(URL, json=payload()).status_code == 409
    assert alert.status == "resolved"
    db.add.assert_not_called()
    db.rollback.assert_called_once()


def test_idempotent_retry_does_not_add_audit(harness):
    client, db, alert = harness
    alert.status = "investigating"
    assert client.patch(URL, json=payload()).status_code == 200
    db.add.assert_not_called()


def test_commit_failure_rolls_back_and_returns_safe_error(harness):
    client, db, _ = harness
    db.commit.side_effect = SQLAlchemyError("private database details")
    response = client.patch(URL, json=payload())
    assert response.status_code == 503
    assert "private" not in response.text
    db.rollback.assert_called_once()


def test_active_investigation_prevents_closing_alert(harness):
    client, db, alert = harness
    db.scalar.side_effect = [alert, UUID(int=500)]
    data = payload()
    data["status"] = "resolved"
    assert client.patch(URL, json=data).status_code == 409
    assert alert.status == "open"
    db.add.assert_not_called()


def test_audit_history_minimizes_data_and_has_pagination(harness):
    client, db, _ = harness
    row = SimpleNamespace(id=UUID(int=500), action="security_alert.status_changed",
        created_at=datetime.now(timezone.utc), actor_ref="private@example.com", ip_address="192.0.2.1",
        details={"reason": "Reviewed", "previous_status": "open", "new_status": "investigating", "private": "secret"})
    db.scalars.return_value.all.return_value = [row, row]
    response = client.get(URL + "/history?limit=1")
    assert response.status_code == 200
    assert response.json()["has_more"] is True
    assert len(response.json()["items"]) == 1
    assert "private" not in response.text and "192.0.2.1" not in response.text


@pytest.mark.parametrize("path", ["", "/history"])
def test_anonymous_cannot_read_details_or_history(harness, path):
    client, db, _ = harness
    app.dependency_overrides.pop(get_current_staff_user)
    assert client.get(URL + path).status_code == 401
    db.scalar.assert_not_called()
