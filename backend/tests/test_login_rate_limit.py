from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app

from app.services.login_rate_limit import reserve_login_attempt


def test_shared_login_limit_and_window_reset(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'limit.db'}")
    from app.models.login_rate_limit import LoginRateLimit
    LoginRateLimit.__table__.create(engine)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for _ in range(5):
        with Session(engine) as db:
            assert reserve_login_attempt(db, email="a@example.test", client_ip="192.0.2.1", now=now) is None
    with Session(engine) as db:
        assert reserve_login_attempt(db, email="a@example.test", client_ip="192.0.2.2", now=now) > 0
    with Session(engine) as db:
        assert reserve_login_attempt(db, email="b@example.test", client_ip="192.0.2.2", now=now) is None
    for index in range(18):
        with Session(engine) as db:
            assert reserve_login_attempt(db, email=f"other{index}@example.test", client_ip="192.0.2.2", now=now) is None
    with Session(engine) as db:
        assert reserve_login_attempt(db, email="last@example.test", client_ip="192.0.2.2", now=now) > 0
    with Session(engine) as db:
        assert reserve_login_attempt(db, email="a@example.test", client_ip="192.0.2.1", now=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc)) is None
    engine.dispose()


def test_login_returns_429_and_fails_closed_when_store_is_missing(tmp_path):
    from app.models.login_rate_limit import LoginRateLimit
    from app.models.staff_user import StaffUser
    engine = create_engine(f"sqlite:///{tmp_path / 'api-limit.db'}", connect_args={"check_same_thread": False})
    LoginRateLimit.__table__.create(engine)
    StaffUser.__table__.create(engine)

    def override_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            responses = [client.post("/api/v1/auth/login", data={"username": "missing@example.test", "password": "bad"}) for _ in range(6)]
            assert [response.status_code for response in responses] == [401] * 5 + [429]
            assert int(responses[-1].headers["Retry-After"]) > 0
            LoginRateLimit.__table__.drop(engine)
            response = client.post("/api/v1/auth/login", data={"username": "missing@example.test", "password": "bad"})
            assert response.status_code == 503
            assert "missing@example.test" not in response.text
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_concurrent_requests_share_one_bucket(tmp_path):
    from app.models.login_rate_limit import LoginRateLimit
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent-limit.db'}", connect_args={"timeout": 20})
    LoginRateLimit.__table__.create(engine)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def attempt(_):
        with Session(engine) as db:
            return reserve_login_attempt(db, email="same@example.test", client_ip="192.0.2.1", now=now)

    with ThreadPoolExecutor(max_workers=10) as pool:
        outcomes = list(pool.map(attempt, range(10)))
    assert sum(value is None for value in outcomes) == 5
    assert sum(value is not None for value in outcomes) == 5
    engine.dispose()
