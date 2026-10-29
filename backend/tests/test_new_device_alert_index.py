
"""Verify SQLAlchemy new-device alert index metadata."""

from app.models.alert import Alert


INDEX_NAME = "uq_alerts_new_device_login_event"


def get_index():
    matches = [
        index
        for index in Alert.__table__.indexes
        if index.name == INDEX_NAME
    ]
    assert len(matches) == 1
    return matches[0]


def test_new_device_index_exists():
    assert get_index().name == INDEX_NAME


def test_new_device_index_is_unique():
    assert get_index().unique is True


def test_new_device_index_has_correct_columns():
    columns = [c.name for c in get_index().columns]
    assert columns == ["alert_type", "login_event_id"]


def test_new_device_index_is_partial():
    index = get_index()
    condition = str(
        index.dialect_options["postgresql"]["where"]
    )
    assert "NEW_DEVICE_LOGIN" in condition
    assert "login_event_id IS NOT NULL" in condition


def test_failed_login_index_is_preserved():
    names = {
        index.name
        for index in Alert.__table__.indexes
    }
    assert "uq_alerts_failed_login_event" in names
