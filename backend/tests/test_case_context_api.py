from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import cases
from app.api.dependencies import get_current_staff_user
from app.db.session import get_db


def test_case_context_redacts_snapshot_and_audit_identity():
    case_id, event_id = uuid4(), uuid4()
    evidence = {
        "rule_code": "NEW_DEVICE_LOGIN", "triggering_event_id": str(event_id),
        "evidence_event_ids": [str(event_id)], "event_count": 1,
        "private_fingerprint": "must-not-leak",
    }
    audit = SimpleNamespace(
        id=uuid4(), action="CASE_UPDATED", created_at=datetime.now(timezone.utc),
        actor_ref="private@example.test", ip_address="192.0.2.1",
        details={"previous_status": "open", "new_status": "investigating",
                 "reason": "synthetic review", "private": "must-not-leak"},
    )
    result = cases.build_case_context(case_id, evidence, [audit], False).model_dump(mode="json")
    assert result["evidence"]["event_count"] == 1
    assert result["audit"][0]["new_status"] == "investigating"
    assert "private_fingerprint" not in str(result)
    assert "private@example.test" not in str(result)
    assert "192.0.2.1" not in str(result)
    assert "must-not-leak" not in str(result)


def test_case_context_requires_case_read_before_database(monkeypatch):
    app = FastAPI()
    app.include_router(cases.router)
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(cases, "load_case_context", lambda *args, **kwargs: (
        _ for _ in ()
    ).throw(AssertionError("unauthorized case context read")))
    with TestClient(app) as client:
        response = client.get(f"/api/v1/cases/{uuid4()}/context")
    assert response.status_code == 401


def test_reviewer_can_read_case_scoped_context(monkeypatch):
    app = FastAPI()
    app.include_router(cases.router)
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        role="reviewer", email="reviewer@bankguard.demo", is_active=True
    )
    app.dependency_overrides[get_db] = lambda: object()
    case_id = uuid4()
    monkeypatch.setattr(cases, "load_case_context", lambda *args, **kwargs: (
        case_id, None, [], False
    ))
    with TestClient(app) as client:
        response = client.get(f"/api/v1/cases/{case_id}/context")
    assert response.status_code == 200
    assert response.json() == {"case_id": str(case_id), "evidence": None,
                               "audit": [], "has_more": False}


def test_security_analyst_cannot_read_case_context(monkeypatch):
    app = FastAPI()
    app.include_router(cases.router)
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        role="security_analyst", email="security@bankguard.demo", is_active=True
    )
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(cases, "load_case_context", lambda *args, **kwargs: (
        _ for _ in ()
    ).throw(AssertionError("unauthorized case context read")))
    with TestClient(app) as client:
        response = client.get(f"/api/v1/cases/{uuid4()}/context")
    assert response.status_code == 403


def test_case_context_missing_case_is_404(monkeypatch):
    app = FastAPI()
    app.include_router(cases.router)
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        role="reviewer", email="reviewer@bankguard.demo", is_active=True
    )
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(cases, "load_case_context", lambda *args, **kwargs: (
        _ for _ in ()
    ).throw(cases.CaseNotFoundError()))
    with TestClient(app) as client:
        response = client.get(f"/api/v1/cases/{uuid4()}/context")
    assert response.status_code == 404
