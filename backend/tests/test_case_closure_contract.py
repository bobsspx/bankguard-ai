from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import cases
from app.api.dependencies import get_current_staff_user
from app.db.session import get_db
from app.services.case_management import StaleCaseStatusError


def test_admin_cannot_close_case_without_reviewer_decision(monkeypatch):
    app = FastAPI()
    app.include_router(cases.router)
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        role="admin", email="admin@bankguard-demo.com", is_active=True
    )
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(cases, "update_case", lambda *args, **kwargs: (
        _ for _ in ()
    ).throw(AssertionError("case update bypassed reviewer")))

    with TestClient(app) as client:
        response = client.patch(f"/api/v1/cases/{uuid4()}", json={"expected_status": "pending_review", "expected_updated_at": "2026-11-17T00:00:00Z", "status": "closed"})

    assert response.status_code == 403
    assert "reviewer" in response.json()["detail"].lower()


def test_status_change_requires_investigation_note(monkeypatch):
    app = FastAPI()
    app.include_router(cases.router)
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        role="fraud_analyst", email="analyst@bankguard-demo.com", is_active=True
    )
    app.dependency_overrides[get_db] = lambda: object()
    monkeypatch.setattr(cases, "update_case", lambda *args, **kwargs: (
        _ for _ in ()
    ).throw(AssertionError("status changed without investigation note")))

    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/cases/{uuid4()}",
            json={"expected_status": "investigating", "expected_updated_at": "2026-11-17T00:00:00Z", "status": "pending_review", "note": "   "},
        )

    assert response.status_code == 422


def test_stale_case_patch_returns_conflict_without_audit(monkeypatch):
    app = FastAPI()
    app.include_router(cases.router)
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        role="fraud_analyst", email="analyst@bankguard-demo.com", is_active=True
    )
    app.dependency_overrides[get_db] = lambda: object()

    def stale(*args, **kwargs):
        raise StaleCaseStatusError("Case changed. Refresh and retry.")

    monkeypatch.setattr(cases, "update_case", stale)
    monkeypatch.setattr(cases, "write_audit_log", lambda *args, **kwargs: (
        _ for _ in ()
    ).throw(AssertionError("stale edit wrote audit")))
    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/cases/{uuid4()}",
            json={"expected_status": "open", "expected_updated_at": "2026-11-17T00:00:00Z",
                  "priority": "high"},
        )
    assert response.status_code == 409
    assert "refresh" in response.json()["detail"].lower()
