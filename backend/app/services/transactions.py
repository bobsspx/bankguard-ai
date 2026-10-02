import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.device import Device
from app.models.transaction import Transaction
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilters,
)


class AccountNotFoundError(Exception):
    pass


class DeviceNotFoundError(Exception):
    pass


class DeviceAccountMismatchError(Exception):
    pass


class DuplicateTransactionError(Exception):
    pass


def list_transactions(
    db: Session,
    filters: TransactionFilters,
):
    conditions = []

    if filters.account_ref:
        conditions.append(
            Account.account_ref
            == filters.account_ref
        )

    if filters.country_code:
        conditions.append(
            Transaction.country_code
            == filters.country_code
        )

    if filters.channel:
        conditions.append(
            Transaction.channel
            == filters.channel
        )

    if filters.status:
        conditions.append(
            Transaction.status
            == filters.status
        )

    if filters.min_amount is not None:
        conditions.append(
            Transaction.amount
            >= filters.min_amount
        )

    if filters.max_amount is not None:
        conditions.append(
            Transaction.amount
            <= filters.max_amount
        )

    if filters.start_at:
        conditions.append(
            Transaction.occurred_at
            >= filters.start_at
        )

    if filters.end_at:
        conditions.append(
            Transaction.occurred_at
            <= filters.end_at
        )

    count_statement = (
        select(
            func.count(Transaction.id)
        )
        .join(
            Account,
            Transaction.account_id
            == Account.id,
        )
        .where(*conditions)
    )

    total = db.scalar(
        count_statement
    ) or 0

    statement = (
        select(
            Transaction,
            Account.account_ref,
            Device.device_ref,
        )
        .join(
            Account,
            Transaction.account_id
            == Account.id,
        )
        .outerjoin(
            Device,
            Transaction.device_id
            == Device.id,
        )
        .where(*conditions)
        .order_by(
            Transaction.occurred_at.desc()
        )
        .offset(filters.offset)
        .limit(filters.limit)
    )

    rows = db.execute(
        statement
    ).all()

    return total, rows


def get_transaction(
    db: Session,
    transaction_id: uuid.UUID,
):
    statement = (
        select(
            Transaction,
            Account.account_ref,
            Device.device_ref,
        )
        .join(
            Account,
            Transaction.account_id
            == Account.id,
        )
        .outerjoin(
            Device,
            Transaction.device_id
            == Device.id,
        )
        .where(
            Transaction.id
            == transaction_id
        )
    )

    return db.execute(
        statement
    ).first()


def create_transaction(
    db: Session,
    payload: TransactionCreate,
) -> Transaction:
    account = db.scalar(
        select(Account).where(
            Account.account_ref
            == payload.account_ref
        )
    )

    if account is None:
        raise AccountNotFoundError

    device = None

    if payload.device_ref:
        device = db.scalar(
            select(Device).where(
                Device.device_ref
                == payload.device_ref
            )
        )

        if device is None:
            raise DeviceNotFoundError

        if device.account_id != account.id:
            raise DeviceAccountMismatchError

    existing = db.scalar(
        select(Transaction).where(
            Transaction.transaction_ref
            == payload.transaction_ref
        )
    )

    if existing is not None:
        raise DuplicateTransactionError

    transaction = Transaction(
        transaction_ref=payload.transaction_ref,
        account_id=account.id,
        device_id=(
            device.id
            if device
            else None
        ),
        amount=payload.amount,
        currency=payload.currency,
        transaction_type=(
            payload.transaction_type
        ),
        merchant_category=(
            payload.merchant_category
        ),
        country_code=payload.country_code,
        channel=payload.channel,
        ip_address=(
            str(payload.ip_address)
            if payload.ip_address
            else None
        ),
        status=payload.status,
        occurred_at=payload.occurred_at,
    )

    db.add(transaction)

    try:
        db.flush()

    except IntegrityError as exc:
        db.rollback()

        raise DuplicateTransactionError from exc

    return transaction