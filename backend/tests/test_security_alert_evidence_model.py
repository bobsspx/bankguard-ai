
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB

from app.models.security_alert_evidence import (
    SecurityAlertEvidence,
)


def test_evidence_table_name():
    assert (
        SecurityAlertEvidence.__tablename__
        == "security_alert_evidence"
    )


def test_evidence_uses_jsonb():
    column = SecurityAlertEvidence.__table__.c.snapshot

    assert isinstance(column.type, JSONB)
    assert column.nullable is False


def test_evidence_links_to_alert():
    column = SecurityAlertEvidence.__table__.c.alert_id

    targets = {
        fk.target_fullname
        for fk in column.foreign_keys
    }

    assert targets == {"alerts.id"}


def test_one_snapshot_per_alert_constraint():
    constraints = [
        item
        for item in SecurityAlertEvidence.__table__.constraints
        if isinstance(item, UniqueConstraint)
    ]

    assert any(
        item.name == "uq_security_alert_evidence_alert_id"
        and [col.name for col in item.columns] == ["alert_id"]
        for item in constraints
    )
