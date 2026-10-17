"""Authenticated shadow scoring. Never persists or changes operational decisions."""
from datetime import datetime, timezone
import hashlib
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import engine
from app.ml.baseline import DEFAULT_MODEL, load_model, predict
from app.models.fraud_score import FraudScore
from app.models.transaction import Transaction
from app.services.ml_feature_store import FeatureTransactionNotFoundError, load_transaction_features
from app.ml.baseline import (
    DEFAULT_MODEL,
    load_model,
    predict,
    find_unseen_categories,
)

router = APIRouter(prefix='/api/v1/ml', tags=['ml-shadow'])


class RuleSnapshot(BaseModel):
    rule_score: float
    final_score: float
    risk_level: str
    model_version: str
    scored_at: datetime


class MLInspection(BaseModel):
    transaction_id: UUID
    unseen_categories: list[str] = Field(default_factory=list)
    transaction_ref: str
    amount: str
    currency: str
    transaction_status: str
    occurred_at: datetime
    mode: str = 'shadow'
    training_source: str = 'synthetic_latent_scenario'
    model_version: str
    model_sha256: str
    feature_version: str
    ml_score: float = Field(ge=0, le=100)
    threshold_score: float = Field(ge=0, le=100)
    above_threshold: bool
    evaluated_at: datetime
    rule: RuleSnapshot | None
    features: dict[str, float | int | str | None]


def read_snapshot(transaction_id):
    # Auth has its own session; snapshot uses a fresh read-only transaction.
    with engine.connect().execution_options(isolation_level='REPEATABLE READ') as connection:
        with connection.begin():
            connection.execute(text('SET TRANSACTION READ ONLY'))
            with Session(bind=connection, autoflush=False) as db:
                features = load_transaction_features(db, transaction_id)
                transaction = db.execute(select(Transaction.transaction_ref, Transaction.amount,
                    Transaction.currency, Transaction.status, Transaction.occurred_at).where(
                        Transaction.id == transaction_id)).mappings().one()
                rule = db.execute(select(FraudScore.rule_score, FraudScore.final_score,
                    FraudScore.risk_level, FraudScore.model_version, FraudScore.scored_at).where(
                        FraudScore.transaction_id == transaction_id)).mappings().one_or_none()
                return features, dict(transaction), dict(rule) if rule is not None else None


@router.get('/transactions/{transaction_id}', response_model=MLInspection)
def inspect_transaction(transaction_id: UUID, response: Response,
                        _user=Depends(require_permission('fraud.read'))):
    response.headers['Cache-Control'] = 'no-store'
    try:
        model = load_model()
        model_hash = hashlib.sha256(DEFAULT_MODEL.read_bytes()).hexdigest()
    except (OSError, ValueError, TypeError):
        raise HTTPException(503, 'ML model unavailable. Check the installed model artifact.')
    try:
        row, transaction, rule = read_snapshot(transaction_id)
        probability = predict(model, row.as_dict())
        return MLInspection(transaction_id=transaction_id,
            transaction_ref=transaction['transaction_ref'], amount=str(transaction['amount']),
            currency=transaction['currency'], transaction_status=transaction['status'],
            occurred_at=transaction['occurred_at'], model_version=model['model_version'],
            model_sha256=model_hash, feature_version=row.feature_version,
            ml_score=round(probability * 100, 4), threshold_score=model['threshold'] * 100,
            above_threshold=probability >= model['threshold'], evaluated_at=datetime.now(timezone.utc),
            rule=rule,
            features=row.as_dict(),
            unseen_categories=find_unseen_categories(
                model,
                row.as_dict(),
            ),
        )
    except FeatureTransactionNotFoundError:
        raise HTTPException(404, 'Transaction not found.')
    except (SQLAlchemyError, ValueError, OverflowError):
        raise HTTPException(503, 'ML inspection unavailable. Check transaction data and database access.')
