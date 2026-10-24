
"""Add failed-login alert deduplication index.

Revision ID: 7a2c91d84f30
Revises: 0bed84b6e331
"""

from alembic import op
import sqlalchemy as sa


revision = "7a2c91d84f30"
down_revision = "0bed84b6e331"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_alerts_failed_login_event",
        "alerts",
        ["alert_type", "login_event_id"],
        unique=True,
        postgresql_where=sa.text(
            "alert_type = 'FAILED_LOGIN_BURST' "
            "AND login_event_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_alerts_failed_login_event",
        table_name="alerts",
    )
