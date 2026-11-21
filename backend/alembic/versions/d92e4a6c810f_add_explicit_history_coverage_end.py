"""Add an explicit coverage endpoint and attestation reference.

Existing rows remain untrusted by the full verifier until an operator supplies
evidence. This migration never infers coverage endpoints from verified_at.
"""
from alembic import op
import sqlalchemy as sa

revision = "d92e4a6c810f"
down_revision = "676b91fff524"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("device_history_coverage", sa.Column("coverage_ended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("device_history_coverage", sa.Column("verification_reference", sa.String(200), nullable=True))
    op.create_check_constraint(
        "ck_device_history_coverage_interval", "device_history_coverage",
        "coverage_ended_at IS NULL OR (coverage_ended_at >= coverage_started_at "
        "AND verified_at IS NOT NULL AND verified_at >= coverage_ended_at)",
    )


def downgrade():
    op.drop_constraint("ck_device_history_coverage_interval", "device_history_coverage", type_="check")
    op.drop_column("device_history_coverage", "verification_reference")
    op.drop_column("device_history_coverage", "coverage_ended_at")
