"""Add shared login attempt buckets."""
from alembic import op
import sqlalchemy as sa

revision = "f7a91c82d4e0"
down_revision = "d92e4a6c810f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "login_rate_limits",
        sa.Column("scope", sa.String(16), primary_key=True),
        sa.Column("key_hash", sa.String(64), primary_key=True),
        sa.Column("window_start", sa.BigInteger, primary_key=True),
        sa.Column("attempts", sa.Integer, nullable=False),
    )
    op.create_index("ix_login_rate_limits_window_start", "login_rate_limits", ["window_start"])


def downgrade():
    op.drop_index("ix_login_rate_limits_window_start", table_name="login_rate_limits")
    op.drop_table("login_rate_limits")
