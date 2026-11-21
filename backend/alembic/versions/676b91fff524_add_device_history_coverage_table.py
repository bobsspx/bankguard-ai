"""add device history coverage table

Revision ID: 676b91fff524
Revises: b61f2a8d903e
Create Date: 2026-10-30 16:49:29.405402

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '676b91fff524'
down_revision: Union[str, Sequence[str], None] = 'b61f2a8d903e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "device_history_coverage",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "coverage_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "verification_source",
            sa.String(length=100),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="unverified",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            name="uq_device_history_coverage_account",
        ),
        sa.CheckConstraint(
            "status IN ('unverified', 'verified')",
            name="ck_device_history_coverage_status",
        ),
        sa.CheckConstraint(
            "status <> 'verified' OR "
            "(verified_at IS NOT NULL "
            "AND verification_source IS NOT NULL)",
            name="ck_device_history_coverage_verification",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("device_history_coverage")
