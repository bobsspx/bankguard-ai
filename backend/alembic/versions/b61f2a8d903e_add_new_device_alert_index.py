
"""Add unique index for new-device security alerts.

Revision ID: b61f2a8d903e
Revises: 9c4e71b205a6
"""

from alembic import op
import sqlalchemy as sa

revision = "b61f2a8d903e"
down_revision = "9c4e71b205a6"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_alerts_new_device_login_event"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        "alerts",
        ["alert_type", "login_event_id"],
        unique=True,
        postgresql_where=sa.text(
            "alert_type = 'NEW_DEVICE_LOGIN' "
            "AND login_event_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        INDEX_NAME,
        table_name="alerts",
    )
