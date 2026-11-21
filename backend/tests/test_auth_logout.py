from uuid import uuid4

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.session import get_db
from app.api.dependencies import get_current_staff_user
from app.main import app
from app.models.staff_user import StaffUser


def test_logout_revokes_old_jwt_and_rejects_replay(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    StaffUser.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    user_id = uuid4()
    with sessions() as db:
        db.add(StaffUser(id=user_id, email="reviewer@bankguard.demo", password_hash=hash_password("synthetic-password"),
                         role="reviewer", is_active=True, session_version=1))
        db.commit()

    def override_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    audit_calls = []
    monkeypatch.setattr(auth, "write_audit_log", lambda *args, **kwargs: audit_calls.append(kwargs), raising=False)
    token = create_access_token(user_id=user_id, email="reviewer@bankguard.demo", role="reviewer", session_version=1)
    headers = {"Authorization": f"Bearer {token}"}
    expired_payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                                 options={"verify_exp": False}, audience=settings.jwt_audience,
                                 issuer=settings.jwt_issuer)
    expired_payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
            assert client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
            assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
            assert client.get("/api/v1/cases", headers=headers).status_code == 401
            assert client.post("/api/v1/auth/logout", headers=headers).status_code == 401
        with sessions() as db:
            assert db.scalar(select(StaffUser.session_version).where(StaffUser.id == user_id)) == 2
        assert len(audit_calls) == 1
        assert audit_calls[0]["action"] == "AUTH_LOGOUT"
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_logout_audit_failure_rolls_back_revocation(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    StaffUser.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    user_id = uuid4()
    with sessions() as db:
        db.add(StaffUser(id=user_id, email="reviewer@bankguard.demo", password_hash=hash_password("synthetic-password"),
                         role="reviewer", is_active=True, session_version=1))
        db.commit()

    def override_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr(auth, "write_audit_log", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("audit failed")), raising=False)
    token = create_access_token(user_id=user_id, email="reviewer@bankguard.demo", role="reviewer", session_version=1)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.post("/api/v1/auth/logout", headers=headers).status_code == 500
            assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
        with sessions() as db:
            assert db.scalar(select(StaffUser.session_version).where(StaffUser.id == user_id)) == 1
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_stale_logout_version_cannot_revoke_a_newer_session(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    StaffUser.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    user_id = uuid4()
    with sessions() as db:
        db.add(StaffUser(id=user_id, email="reviewer@bankguard.demo", password_hash=hash_password("synthetic-password"),
                         role="reviewer", is_active=True, session_version=2))
        db.commit()

    def override_db():
        with sessions() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        id=user_id, email="reviewer@bankguard.demo", session_version=1
    )
    audit_calls = []
    monkeypatch.setattr(auth, "write_audit_log", lambda *args, **kwargs: audit_calls.append(kwargs))
    try:
        with TestClient(app) as client:
            assert client.post("/api/v1/auth/logout").status_code == 401
        with sessions() as db:
            assert db.scalar(select(StaffUser.session_version).where(StaffUser.id == user_id)) == 2
        assert audit_calls == []
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

