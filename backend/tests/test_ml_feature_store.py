from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy import create_engine

from app.models.transaction import Transaction
from app.services.ml_feature_store import (
    FeatureTransactionNotFoundError, TransactionSnapshot,
    history_statement, load_transaction_features,
)

def uid(n):
    return UUID(int=(0xabcdef << 104) + n)


NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def record(n=1, **changes):
    row = dict(id=uid(n), account_id=uid(100), device_id=None,
               amount=Decimal('100'), currency='USD', transaction_type='transfer',
               merchant_category=None, country_code='LA', channel='mobile',
               ip_address=None, occurred_at=NOW, created_at=NOW)
    row.update(changes)
    return row


def session(target, history=()):
    db = MagicMock()
    db.new = db.dirty = db.deleted = set()
    db.no_autoflush = nullcontext()
    first = MagicMock()
    first.mappings.return_value.one_or_none.return_value = target
    second = MagicMock()
    second.mappings.return_value = history
    db.execute.side_effect = [first, second]
    return db


def test_adapter_projects_features_without_writing():
    db = session(record(), [record(2, occurred_at=NOW-timedelta(minutes=1))])
    result = load_transaction_features(db, uid(1))
    assert result.as_dict()['history_count_30d'] == 1
    assert result.as_dict()['account_country_mismatch'] is None
    for name in ('flush', 'commit', 'rollback', 'add', 'delete', 'close'):
        getattr(db, name).assert_not_called()


def test_missing_target_stops_before_history_query():
    db = session(None)
    with pytest.raises(FeatureTransactionNotFoundError):
        load_transaction_features(db, uid(9))
    assert db.execute.call_count == 1


@pytest.mark.parametrize('pending', ['new', 'dirty', 'deleted'])
def test_pending_mutations_rejected(pending):
    db = session(record())
    setattr(db, pending, {object()})
    with pytest.raises(ValueError, match='pending writes'):
        load_transaction_features(db, uid(1))
    db.execute.assert_not_called()


def test_naive_target_rejected_before_history_query():
    db = session(record(occurred_at=NOW.replace(tzinfo=None)))
    with pytest.raises(ValueError, match='Timezone-aware'):
        load_transaction_features(db, uid(1))
    assert db.execute.call_count == 1


def test_database_query_filters_and_preserves_currency_rows():
    # Actual SQL execution against an isolated SQLite table tests WHERE logic.
    # PostgreSQL timezone decoding is checked separately by the live smoke CLI.
    engine = create_engine('sqlite://')
    table = Transaction.__table__
    table.create(engine)
    rows = [record(),
            record(2, occurred_at=NOW-timedelta(minutes=10)),
            record(3, occurred_at=NOW-timedelta(days=30)),
            record(4, occurred_at=NOW-timedelta(days=30, seconds=1)),
            record(5),
            record(6, occurred_at=NOW+timedelta(seconds=1)),
            record(7, occurred_at=NOW-timedelta(minutes=1), created_at=NOW+timedelta(seconds=1)),
            record(8, occurred_at=NOW-timedelta(minutes=1), account_id=uid(999)),
            record(9, occurred_at=NOW-timedelta(minutes=1), currency='LAK')]
    with engine.begin() as conn:
        conn.execute(table.insert(), [dict(r, transaction_ref=str(r['id']), status='completed') for r in rows])
        results = conn.execute(history_statement(TransactionSnapshot(**record()))).mappings().all()
    assert [r['id'] for r in results] == [uid(n) for n in (3, 2, 9)]
    engine.dispose()


def test_projection_excludes_outcomes_and_mutable_profile_tables():
    from sqlalchemy.dialects import postgresql
    statement = history_statement(TransactionSnapshot(**record()))
    names = set(statement.selected_columns.keys())
    assert not names & {'status', 'rule_score', 'final_score', 'decision', 'trusted'}
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert 'LIMIT' not in sql
    assert 'accounts' not in sql and 'devices' not in sql
