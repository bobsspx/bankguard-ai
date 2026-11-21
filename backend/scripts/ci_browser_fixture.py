"""Create or remove disposable browser data in the guarded local CI database."""

import json
import os
from pathlib import Path
import secrets
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.account import Account
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.investigation_case import InvestigationCase
from app.models.staff_user import StaffUser
from app.models.transaction import Transaction
from scripts.run_ci_postgres import is_ci_target


def main() -> None:
    if not is_ci_target(os.environ.get("DATABASE_URL", ""), os.environ.get("CI_POSTGRES_TEST")):
        raise SystemExit("Disposable local CI PostgreSQL target required")
    if os.environ.get("APP_ENV") != "test":
        raise SystemExit("APP_ENV=test required")
    fixture_path = Path(os.environ["CI_BROWSER_AUTH_FILE"])
    if fixture_path.parent != Path(os.environ["RUNNER_TEMP"]):
        raise SystemExit("Browser fixture must stay in runner temp")
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    engine = create_engine(os.environ["DATABASE_URL"], hide_parameters=True)
    try:
        if mode == "create":
            if fixture_path.exists():
                raise SystemExit("Browser fixture already exists")
            marker = uuid4().hex[:12]
            user_id, account_id, alert_id, case_id = (uuid4() for _ in range(4))
            email = f"ci-{marker}@bankguard.demo"
            password = secrets.token_urlsafe(24)
            account_ref = f"CI-ACC-{marker}"
            with Session(engine) as db, db.begin():
                db.add(StaffUser(id=user_id, email=email, password_hash=hash_password(password),
                                 role="fraud_analyst", is_active=True, session_version=1))
                db.add(Account(id=account_id, account_ref=account_ref, customer_ref=f"CI-{marker}",
                               account_type="checking", country_code="US", currency="USD"))
                db.flush()
                first_transaction = None
                for index in range(30):
                    transaction = Transaction(
                        id=uuid4(), transaction_ref=f"CI-TXN-{marker}-{index:02d}",
                        account_id=account_id, amount=Decimal(index + 1), currency="USD",
                        transaction_type="transfer", country_code="US", channel="web",
                        status="completed", occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=index),
                    )
                    db.add(transaction)
                    if index == 0:
                        first_transaction = transaction
                db.flush()
                db.add(Alert(id=alert_id, transaction_id=first_transaction.id, alert_type="RULE_MATCH",
                             severity="medium", status="investigating", title="CI synthetic alert",
                             description="Disposable browser fixture"))
                db.flush()
                db.add(InvestigationCase(id=case_id, case_ref=f"CI-CASE-{marker}", alert_id=alert_id,
                                         status="open", priority="medium", notes="Read-only browser test"))
            record = {"email": email, "password": password, "account_ref": account_ref,
                      "user_id": str(user_id), "account_id": str(account_id),
                      "alert_id": str(alert_id), "case_id": str(case_id)}
            handle = os.open(fixture_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                json.dump(record, stream)
            print("Disposable CI browser fixture created")
        elif mode == "cleanup":
            if not fixture_path.exists():
                return
            record = json.loads(fixture_path.read_text(encoding="utf-8"))
            if not record["email"].startswith("ci-") or not record["email"].endswith(("@bankguard.demo", "@example.test")):
                raise SystemExit("Invalid CI fixture identity")
            user_id = UUID(record["user_id"])
            account_id = UUID(record["account_id"])
            alert_id = UUID(record["alert_id"])
            case_id = UUID(record["case_id"])
            with Session(engine) as db, db.begin():
                db.execute(delete(AuditLog).where(AuditLog.actor_ref == record["email"]))
                db.execute(delete(InvestigationCase).where(InvestigationCase.id == case_id))
                db.execute(delete(Alert).where(Alert.id == alert_id))
                db.execute(delete(Transaction).where(Transaction.account_id == account_id))
                db.execute(delete(Account).where(Account.id == account_id))
                db.execute(delete(StaffUser).where(StaffUser.id == user_id))
            fixture_path.unlink()
            print("Disposable CI browser fixture removed")
        else:
            raise SystemExit("Usage: ci_browser_fixture.py create|cleanup")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
