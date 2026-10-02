"""harden transaction monitoring model

Revision ID: 03f84ae784f8
Revises: 0e8fe4580693
Create Date: 2026-10-02 13:59:53.416779

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '03f84ae784f8'
down_revision: Union[str, Sequence[str], None] = '0e8fe4580693'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Harden transaction monitoring schema."""

    op.create_check_constraint(
        "ck_transactions_type",
        "transactions",
        "transaction_type IN ('transfer', 'card_payment', 'cash_withdrawal', 'bill_payment')",
    )

    op.create_check_constraint(
        "ck_transactions_channel",
        "transactions",
        "channel IN ('mobile', 'web', 'atm', 'branch', 'api')",
    )

    op.create_check_constraint(
        "ck_transactions_status",
        "transactions",
        "status IN ('pending', 'completed', 'declined', 'reversed')",
    )

    op.create_index(
        "ix_transactions_occurred_at",
        "transactions",
        ["occurred_at"],
        unique=False,
    )

    op.create_index(
        "ix_transactions_account_occurred_at",
        "transactions",
        ["account_id", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    """Revert transaction monitoring schema hardening."""

    op.drop_index(
        "ix_transactions_account_occurred_at",
        table_name="transactions",
    )

    op.drop_index(
        "ix_transactions_occurred_at",
        table_name="transactions",
    )

    op.drop_constraint(
        "ck_transactions_status",
        "transactions",
        type_="check",
    )

    op.drop_constraint(
        "ck_transactions_channel",
        "transactions",
        type_="check",
    )

    op.drop_constraint(
        "ck_transactions_type",
        "transactions",
        type_="check",
    )