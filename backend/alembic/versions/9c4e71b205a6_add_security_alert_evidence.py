
"""Add security alert evidence snapshots.

Revision ID: 9c4e71b205a6
Revises: 7a2c91d84f30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "9c4e71b205a6"
down_revision = "7a2c91d84f30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_alert_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("snapshot", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "alert_id",
            name="uq_security_alert_evidence_alert_id",
        ),
    )

    op.create_index(
        "ix_security_alert_evidence_alert_id",
        "security_alert_evidence",
        ["alert_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_alert_evidence_alert_id",
        table_name="security_alert_evidence",
    )
    op.drop_table("security_alert_evidence")
