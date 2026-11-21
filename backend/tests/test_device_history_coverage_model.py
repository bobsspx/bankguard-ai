
from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
)

from app.models.device_history_coverage import (
    DeviceHistoryCoverage,
)


def test_table_name():
    assert (
        DeviceHistoryCoverage.__tablename__
        == "device_history_coverage"
    )


def test_explicit_coverage_end_and_reference_are_not_backfilled():
    columns = DeviceHistoryCoverage.__table__.c
    for name in ("coverage_ended_at", "verification_reference"):
        assert columns[name].nullable is True
        assert columns[name].default is None
        assert columns[name].server_default is None
    assert any(c.name == "ck_device_history_coverage_interval"
               for c in DeviceHistoryCoverage.__table__.constraints)


def test_account_is_required():
    column = DeviceHistoryCoverage.__table__.c.account_id
    assert column.nullable is False


def test_coverage_start_is_required():
    column = (
        DeviceHistoryCoverage.__table__.c.coverage_started_at
    )
    assert column.nullable is False


def test_account_has_unique_constraint():
    constraints = (
        DeviceHistoryCoverage.__table__.constraints
    )
    assert any(
        isinstance(c, UniqueConstraint)
        and c.name == "uq_device_history_coverage_account"
        for c in constraints
    )


def test_verification_constraint_exists():
    constraints = (
        DeviceHistoryCoverage.__table__.constraints
    )
    assert any(
        isinstance(c, CheckConstraint)
        and c.name
        == "ck_device_history_coverage_verification"
        for c in constraints
    )
