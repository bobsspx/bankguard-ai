import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import (
    require_permission,
)
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.schemas.transaction import (
    TransactionCreate,
    TransactionFilters,
    TransactionPage,
    TransactionResponse,
)
from app.services.audit import (
    write_audit_log,
)
from app.services.transactions import (
    AccountNotFoundError,
    DeviceAccountMismatchError,
    DeviceNotFoundError,
    DuplicateTransactionError,
    create_transaction,
    get_transaction,
    list_transactions,
)


router = APIRouter(
    prefix="/api/v1/transactions",
    tags=["transactions"],
)


def make_response(
    transaction,
    account_ref: str,
    device_ref: str | None,
) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        transaction_ref=(
            transaction.transaction_ref
        ),
        account_ref=account_ref,
        device_ref=device_ref,
        amount=transaction.amount,
        currency=transaction.currency,
        transaction_type=(
            transaction.transaction_type
        ),
        merchant_category=(
            transaction.merchant_category
        ),
        country_code=(
            transaction.country_code
        ),
        channel=transaction.channel,
        ip_address=transaction.ip_address,
        status=transaction.status,
        occurred_at=transaction.occurred_at,
        created_at=transaction.created_at,
    )


@router.get(
    "",
    response_model=TransactionPage,
)
def read_transactions(
    filters: Annotated[
        TransactionFilters,
        Query(),
    ],
    db: Session = Depends(get_db),
    _user: StaffUser = Depends(
        require_permission(
            "transactions.read"
        )
    ),
):
    total, rows = list_transactions(
        db,
        filters,
    )

    items = [
        make_response(
            transaction,
            account_ref,
            device_ref,
        )
        for (
            transaction,
            account_ref,
            device_ref,
        ) in rows
    ]

    return TransactionPage(
        total=total,
        limit=filters.limit,
        offset=filters.offset,
        items=items,
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
)
def read_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: StaffUser = Depends(
        require_permission(
            "transactions.read"
        )
    ),
):
    row = get_transaction(
        db,
        transaction_id,
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found.",
        )

    transaction, account_ref, device_ref = row

    return make_response(
        transaction,
        account_ref,
        device_ref,
    )


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_transaction(
    request: Request,
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    user: StaffUser = Depends(
        require_permission(
            "transactions.ingest"
        )
    ),
):
    try:
        transaction = create_transaction(
            db,
            payload,
        )

    except AccountNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Account not found.",
        )

    except DeviceNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Device not found.",
        )

    except DeviceAccountMismatchError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Device does not belong "
                "to the account."
            ),
        )

    except DuplicateTransactionError:
        raise HTTPException(
            status_code=409,
            detail=(
                "Transaction reference "
                "already exists."
            ),
        )

    client_ip = (
        request.client.host
        if request.client
        else None
    )

    write_audit_log(
        db,
        actor_ref=user.email,
        action="TRANSACTION_INGESTED",
        resource_type="transaction",
        resource_id=str(transaction.id),
        ip_address=client_ip,
        details={
            "transaction_ref":
                transaction.transaction_ref,
            "account_ref":
                payload.account_ref,
        },
    )

    db.commit()
    db.refresh(transaction)

    row = get_transaction(
        db,
        transaction.id,
    )

    transaction, account_ref, device_ref = row

    return make_response(
        transaction,
        account_ref,
        device_ref,
    )