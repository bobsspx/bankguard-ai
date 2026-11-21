"""Disposable PostgreSQL checks; only run by scripts/run_ci_postgres.py."""

from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone
import hashlib
import hmac
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.fraud_decision import FraudDecision
from app.models.investigation_case import InvestigationCase
from app.models.login_rate_limit import LoginRateLimit
from app.services.fraud_decision import create_fraud_decision
from app.services.login_rate_limit import ACCOUNT_LIMIT, WINDOW_SECONDS, reserve_login_attempt
from scripts.run_ci_postgres import is_ci_target


@pytest.fixture(scope="module")
def engine():
    assert is_ci_target(os.environ.get("DATABASE_URL", ""), os.environ.get("CI_POSTGRES_TEST"))
    assert settings.app_env == "test"
    result = create_engine(settings.database_url, hide_parameters=True)
    with result.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "f7a91c82d4e0"
    yield result
    result.dispose()


def test_migrated_schema_and_constraints(engine):
    tables = set(inspect(engine).get_table_names())
    assert {"login_rate_limits", "investigation_cases", "fraud_decisions", "audit_logs"} <= tables
    assert any(item["name"] == "ck_fraud_decisions_decision"
               for item in inspect(engine).get_check_constraints("fraud_decisions"))
    assert any(item["name"] == "uq_fraud_decisions_case_id"
               for item in inspect(engine).get_unique_constraints("fraud_decisions"))


def test_case_decision_and_audit_rollback_together(engine):
    alert_id, case_id = uuid4(), uuid4()
    with Session(engine) as db:
        db.add(Alert(id=alert_id, alert_type="NEW_DEVICE_LOGIN", severity="medium",
                     status="investigating", title="CI synthetic", description="CI only"))
        db.flush()
        db.add(InvestigationCase(id=case_id, case_ref=f"CI-{case_id.hex}", alert_id=alert_id,
                                 status="pending_review", priority="medium",
                                 assigned_to="analyst@bankguard.demo", notes="Synthetic CI review"))
        db.flush()
        result = create_fraud_decision(db, case_id=case_id, decision="inconclusive",
                                       decision_reason="Synthetic CI test", reviewer_email="reviewer@bankguard.demo")
        assert result["case"].status == "closed"
        assert result["alert"].status == "resolved"
        db.add(AuditLog(actor_ref=None, action="CI_INVALID", resource_type="case", resource_id=str(case_id)))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Alert).where(Alert.id == alert_id)) == 0
        assert db.scalar(select(func.count()).select_from(InvestigationCase).where(InvestigationCase.id == case_id)) == 0
        assert db.scalar(select(func.count()).select_from(FraudDecision).where(FraudDecision.case_id == case_id)) == 0
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.resource_id == str(case_id))) == 0


def _reserve_in_worker(args):
    email, ip, now = args
    engine = create_engine(os.environ["DATABASE_URL"], hide_parameters=True)
    try:
        with Session(engine) as db:
            return reserve_login_attempt(db, email=email, client_ip=ip, now=now)
    finally:
        engine.dispose()


def test_rate_limit_is_shared_across_processes(engine):
    unique = uuid4().hex
    email, ip = f"ci-{unique}@example.test", f"192.0.2.{int(unique[:2], 16) % 200 + 1}"
    now = datetime.now(timezone.utc)
    window = int(now.timestamp()) // WINDOW_SECONDS * WINDOW_SECONDS
    hashes = [hmac.new(settings.jwt_secret.encode(), f"{scope}:{value}".encode(), hashlib.sha256).hexdigest()
              for scope, value in (("account", email), ("ip", ip))]
    try:
        with ProcessPoolExecutor(max_workers=ACCOUNT_LIMIT + 1) as pool:
            outcomes = list(pool.map(_reserve_in_worker, [(email, ip, now)] * (ACCOUNT_LIMIT + 1)))
        assert sum(value is None for value in outcomes) == ACCOUNT_LIMIT
        assert sum(value is not None for value in outcomes) == 1
        with Session(engine) as db:
            assert db.scalar(select(LoginRateLimit.attempts).where(
                LoginRateLimit.scope == "account", LoginRateLimit.key_hash == hashes[0],
                LoginRateLimit.window_start == window,
            )) == ACCOUNT_LIMIT + 1
    finally:
        with engine.begin() as connection:
            connection.execute(delete(LoginRateLimit).where(LoginRateLimit.window_start == window,
                                                              LoginRateLimit.key_hash.in_(hashes)))
