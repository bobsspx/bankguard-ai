from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api import transactions as transaction_api
from app.api.dependencies import get_current_staff_user
from app.db.session import get_db
from app.schemas.transaction import TransactionFilters
from app.services.transactions import list_transactions


class RecordingSession:
    def scalar(self, statement):
        self.count_sql = str(statement.compile(dialect=postgresql.dialect()))
        return 4

    def execute(self, statement):
        compiled = statement.compile(dialect=postgresql.dialect())
        self.sql = str(compiled)
        self.params = compiled.params
        return self

    def all(self):
        return []


def test_sorting_is_whitelisted_stable_and_precedes_pagination():
    for field, direction, expected in (
        ("occurred_at", "desc", "transactions.occurred_at DESC"),
        ("amount", "asc", "transactions.amount ASC"),
        ("amount", "desc", "transactions.amount DESC"),
        ("transaction_ref", "asc", "transactions.transaction_ref ASC"),
    ):
        db = RecordingSession()
        total, rows = list_transactions(db, TransactionFilters(
            sort_by=field, sort_dir=direction, offset=25, limit=10,
            account_ref="A-1", min_amount=Decimal("10"),
        ))
        assert (total, rows) == (4, [])
        assert expected in db.sql
        assert "transactions.id ASC" in db.sql
        assert db.sql.index("ORDER BY") < db.sql.index("LIMIT")
        assert "accounts.account_ref" in db.count_sql
        assert "transactions.amount" in db.count_sql
        assert 25 in db.params.values() and 10 in db.params.values()


def test_sort_query_validation_and_authorization(monkeypatch):
    app = FastAPI()
    app.include_router(transaction_api.router)
    app.dependency_overrides[get_db] = lambda: None
    captured = []
    monkeypatch.setattr(transaction_api, "list_transactions", lambda db, filters: (captured.append(filters), (0, []))[1])
    with TestClient(app) as client:
        assert client.get("/api/v1/transactions?sort_by=amount&sort_dir=asc").status_code == 401
        app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role="security_analyst")
        assert client.get("/api/v1/transactions?sort_by=amount&sort_dir=asc").status_code == 403
        app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role="fraud_analyst")
        assert client.get("/api/v1/transactions?sort_by=amount&sort_dir=asc").status_code == 200
        assert (captured[-1].sort_by, captured[-1].sort_dir) == ("amount", "asc")
        assert client.get("/api/v1/transactions?sort_by=password_hash").status_code == 422
        assert client.get("/api/v1/transactions?sort_dir=sideways").status_code == 422
