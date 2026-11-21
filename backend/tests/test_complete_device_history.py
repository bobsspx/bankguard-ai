from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.services.new_device_history_verification import (
    TRUSTED_HISTORY_SOURCE, verify_complete_device_history_for_event,
)

NOW = datetime.now(timezone.utc) - timedelta(days=1)
ACCOUNT, EVENT = UUID(int=1), UUID(int=2)


def records():
    account = SimpleNamespace(id=ACCOUNT, created_at=NOW - timedelta(days=30))
    coverage = SimpleNamespace(
        account_id=ACCOUNT, status="verified",
        coverage_started_at=account.created_at,
        verified_at=NOW, verification_source=TRUSTED_HISTORY_SOURCE,
        coverage_ended_at=NOW, verification_reference="synthetic-manifest-1",
    )
    current = SimpleNamespace(id=EVENT, account_id=ACCOUNT, occurred_at=NOW)
    return account, coverage, current


@pytest.mark.parametrize("case", [
    "valid", "late_start", "stale_verification", "untrusted_source",
    "missing_account", "wrong_account", "naive_account", "before_account",
    "future_verification", "missing_coverage", "unverified", "missing_event",
    "missing_end", "before_event_end", "naive_end", "missing_reference", "legacy_source",
])
def test_lifetime_attestation_boundaries(case):
    account, coverage, current = records()
    if case == "late_start":
        coverage.coverage_started_at += timedelta(seconds=1)
    elif case == "stale_verification":
        coverage.verified_at -= timedelta(seconds=1)
    elif case == "untrusted_source":
        coverage.verification_source = "caller-says-complete"
    elif case == "missing_account":
        account = None
    elif case == "wrong_account":
        account.id = UUID(int=99)
    elif case == "naive_account":
        account.created_at = account.created_at.replace(tzinfo=None)
    elif case == "before_account":
        account.created_at = NOW + timedelta(seconds=1)
    elif case == "future_verification":
        coverage.verified_at = NOW + timedelta(days=2)
    elif case == "missing_coverage":
        coverage = None
    elif case == "unverified":
        coverage.status = "unverified"
    elif case == "missing_event":
        current = None
    elif case == "missing_end":
        coverage.coverage_ended_at = None
    elif case == "before_event_end":
        coverage.coverage_ended_at = NOW - timedelta(seconds=1)
    elif case == "naive_end":
        coverage.coverage_ended_at = NOW.replace(tzinfo=None)
    elif case == "missing_reference":
        coverage.verification_reference = " "
    elif case == "legacy_source":
        coverage.verification_source = "bankguard-history-import-v1"

    db = MagicMock(spec=Session)
    db.scalar.side_effect = [current, coverage, account, coverage, current]
    result = verify_complete_device_history_for_event(
        db, account_id=ACCOUNT, current_event_id=EVENT,
    )
    assert result.history_verified is (case == "valid")
    if case == "valid":
        assert result.status == "verified"
    for method in ("add", "flush", "commit", "rollback"):
        getattr(db, method).assert_not_called()
