
"""Persistence safety contract for security alert rules."""

import pytest

from app.models.alert import Alert


RULE_INDEXES = {
    "FAILED_LOGIN_BURST": "uq_alerts_failed_login_event",
    "NEW_DEVICE_LOGIN": "uq_alerts_new_device_login_event",
}


@pytest.mark.parametrize("rule,index_name", RULE_INDEXES.items())
def test_rule_has_unique_partial_index(rule, index_name):
    matching = [
        index for index in Alert.__table__.indexes
        if index.name == index_name
    ]

    assert len(matching) == 1

    index = matching[0]
    assert index.unique is True
    assert [c.name for c in index.columns] == [
        "alert_type",
        "login_event_id",
    ]

    predicate = str(
        index.dialect_options["postgresql"]["where"]
    )

    assert rule in predicate
    assert "login_event_id IS NOT NULL" in predicate


def test_each_rule_uses_distinct_index():
    assert len(set(RULE_INDEXES.values())) == len(RULE_INDEXES)


def test_evidence_snapshot_column_is_jsonb():
    from app.models.security_alert_evidence import (
        SecurityAlertEvidence,
    )
    from sqlalchemy.dialects.postgresql import JSONB

    column = SecurityAlertEvidence.__table__.c.snapshot
    assert isinstance(column.type, JSONB)
