from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api import ml
from app.api.dependencies import get_current_staff_user
from app.ml.build_dataset import build_rows
from app.services.ml_features import FeatureRow, FEATURE_NAMES, FEATURE_VERSION
from app.services.ml_feature_store import FeatureTransactionNotFoundError

ID = UUID(int=1)


def snapshot(_):
    row = build_rows(count=100)[0]
    return (FeatureRow(ID, FEATURE_VERSION, tuple(row['features'][n] for n in FEATURE_NAMES)),
        dict(transaction_ref='DEMO-001', amount=Decimal('184.17'), currency='USD', status='completed',
             occurred_at=datetime(2025, 1, 1, tzinfo=timezone.utc)), None)


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(ml.router)
    monkeypatch.setattr(ml, 'read_snapshot', snapshot)
    with TestClient(app) as client:
        yield client


def test_anonymous_rejected_before_read(client, monkeypatch):
    def forbidden(_):
        pytest.fail('Anonymous request accessed data')
    monkeypatch.setattr(ml, 'read_snapshot', forbidden)
    assert client.get(f'/api/v1/ml/transactions/{ID}').status_code == 401


def test_security_analyst_forbidden_before_read(client, monkeypatch):
    client.app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role='security_analyst')
    monkeypatch.setattr(ml, 'read_snapshot', lambda _: pytest.fail('Unauthorized data access'))
    assert client.get(f'/api/v1/ml/transactions/{ID}').status_code == 403


@pytest.mark.parametrize('role', ['admin', 'fraud_analyst', 'reviewer'])
def test_permitted_roles_real_model_response(client, role):
    client.app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role=role)
    response = client.get(f'/api/v1/ml/transactions/{ID}')
    assert response.status_code == 200
    result = response.json()
    assert result['mode'] == 'shadow'
    assert 0 <= result['ml_score'] <= 100
    assert len(result['features']) == 20
    assert result['rule'] is None
    assert result['model_version'] == 'synthetic-logistic-v1'
    assert response.headers['cache-control'] == 'no-store'


def test_missing_transaction_and_model_errors(client, monkeypatch):
    client.app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role='admin')
    def missing(_):
        raise FeatureTransactionNotFoundError()
    monkeypatch.setattr(ml, 'read_snapshot', missing)
    assert client.get(f'/api/v1/ml/transactions/{ID}').status_code == 404
    def invalid():
        raise ValueError('private model detail')
    monkeypatch.setattr(ml, 'load_model', invalid)
    response = client.get(f'/api/v1/ml/transactions/{ID}')
    assert response.status_code == 503
    assert 'private' not in response.text


def test_invalid_uuid(client):
    client.app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(role='admin')
    assert client.get('/api/v1/ml/transactions/invalid').status_code == 422


def test_snapshot_uses_read_only_isolated_transaction(monkeypatch):
    from unittest.mock import MagicMock
    connection = MagicMock()
    fake_engine = MagicMock()
    fake_engine.connect.return_value.execution_options.return_value.__enter__.return_value = connection
    fake_db = MagicMock()
    session = MagicMock()
    session.return_value.__enter__.return_value = fake_db
    fake_db.execute.return_value.mappings.return_value.one.return_value = {'transaction_ref': 'demo'}
    fake_db.execute.return_value.mappings.return_value.one_or_none.return_value = None
    monkeypatch.setattr(ml, 'engine', fake_engine)
    monkeypatch.setattr(ml, 'Session', session)
    monkeypatch.setattr(ml, 'load_transaction_features', lambda db, transaction_id: 'features')
    result = ml.read_snapshot(ID)
    assert result == ('features', {'transaction_ref': 'demo'}, None)
    fake_engine.connect.return_value.execution_options.assert_called_once_with(isolation_level='REPEATABLE READ')
    assert str(connection.execute.call_args.args[0]) == 'SET TRANSACTION READ ONLY'
    session.assert_called_once_with(bind=connection, autoflush=False)
    for name in ['commit', 'flush', 'add', 'delete']:
        getattr(fake_db, name).assert_not_called()
