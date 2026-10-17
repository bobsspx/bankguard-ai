from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.services.ml_features import FEATURE_NAMES, extract_transaction_features

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def tx(n=1, **changes):
    fields = dict(id=UUID(int=n), account_id=UUID(int=100),
                  device_id=UUID(int=200), amount=Decimal('100'), currency='USD',
                  transaction_type='transfer', merchant_category=None,
                  country_code='LA', channel='mobile', ip_address='203.0.113.1',
                  occurred_at=NOW, created_at=NOW)
    fields.update(changes)
    return SimpleNamespace(**fields)


def features(history=(), **changes):
    return extract_transaction_features(tx(**changes), history).as_dict()


def test_cold_start_preserves_unknowns():
    f = features()
    assert f['history_count_30d'] == 0
    assert f['mean_amount_30d'] is None
    assert f['amount_to_mean_30d'] is None
    assert f['account_country_mismatch'] is None
    assert f['device_unseen_30d'] is None
    assert f['ip_unseen_30d'] is None


def test_past_aggregation():
    f = features([tx(2, occurred_at=NOW-timedelta(minutes=5), amount=Decimal('50')),
                  tx(3, occurred_at=NOW-timedelta(hours=2), amount=Decimal('150'))])
    assert (f['history_count_30d'], f['recent_count_10m'], f['recent_count_24h']) == (2, 1, 2)
    assert (f['mean_amount_30d'], f['amount_to_mean_30d'], f['recent_amount_24h']) == (100, 1, 200)
    assert f['device_unseen_30d'] == f['ip_unseen_30d'] == 0


@pytest.mark.parametrize('minutes,expected', [(0, 0), (-1, 0), (10, 1), (11, 0)])
def test_strict_event_cutoff_and_velocity_boundary(minutes, expected):
    f = features([tx(2, occurred_at=NOW-timedelta(minutes=minutes))])
    assert f['recent_count_10m'] == expected


def test_excludes_self_other_accounts_and_late_arrivals():
    assert features([tx(), tx(2, account_id=UUID(int=999), occurred_at=NOW-timedelta(hours=1)),
                     tx(3, occurred_at=NOW-timedelta(hours=1), created_at=NOW+timedelta(seconds=1))]) == features()


def test_window_boundaries():
    f = features([tx(2, occurred_at=NOW-timedelta(days=30)),
                  tx(3, occurred_at=NOW-timedelta(days=30, seconds=1)),
                  tx(4, occurred_at=NOW-timedelta(days=1))])
    assert f['history_count_30d'] == 2
    assert f['recent_count_24h'] == 1


def test_never_sums_mixed_currencies():
    f = features([tx(2, currency='LAK', occurred_at=NOW-timedelta(minutes=1))])
    assert f['recent_count_10m'] == 1
    assert f['recent_amount_24h'] == 0
    assert f['mean_amount_30d'] is None
    assert f['same_currency_count_30d'] == 0


def test_missing_device_and_ip():
    f = features(device_id=None, ip_address=None)
    assert f['device_missing'] == f['ip_missing'] == 1
    assert f['device_unseen_30d'] is None
    assert f['ip_unseen_30d'] is None


def test_unseen_device_and_ip():
    f = features([tx(2, device_id=UUID(int=201), ip_address='203.0.113.2',
                     occurred_at=NOW-timedelta(minutes=1))])
    assert f['device_unseen_30d'] == f['ip_unseen_30d'] == 1


def test_ipv6_equivalent_forms():
    f = features([tx(2, ip_address='2001:db8::1', occurred_at=NOW-timedelta(minutes=1))],
                 ip_address='2001:0db8:0:0:0:0:0:1')
    assert f['ip_unseen_30d'] == 0


def test_utc_normalization():
    local = NOW.astimezone(timezone(timedelta(hours=7)))
    assert features(occurred_at=local, created_at=local) == features()


@pytest.mark.parametrize('field', ['occurred_at', 'created_at'])
def test_rejects_naive_timestamps(field):
    with pytest.raises(ValueError, match='Timezone-aware'):
        features(**{field: NOW.replace(tzinfo=None)})


@pytest.mark.parametrize('amount', ['0', '-1', 'NaN', 'Infinity'])
def test_rejects_invalid_amounts(amount):
    with pytest.raises(ValueError, match='positive and finite'):
        features(amount=Decimal(amount))


def test_rejects_duplicate_eligible_history():
    past = tx(2, occurred_at=NOW-timedelta(minutes=1))
    with pytest.raises(ValueError, match='Duplicate'):
        features([past, past])


def test_determinism_and_no_mutation():
    history = [tx(2, occurred_at=NOW-timedelta(minutes=1)),
               tx(3, occurred_at=NOW-timedelta(minutes=2))]
    before = [vars(p).copy() for p in history]
    assert features(history) == features(reversed(history))
    assert [vars(p) for p in history] == before


def test_output_allowlist_and_outcome_independence():
    f = features(status='declined', decision='confirmed_fraud', rule_score=100,
                 final_score=100, trusted=False)
    assert f == features()
    assert tuple(f) == FEATURE_NAMES
    assert not {'id', 'account_id', 'device_id', 'ip_address', 'decision', 'status'} & set(f)


@pytest.mark.parametrize('country,expected', [('LA', 0), ('TH', 1)])
def test_explicit_historical_country(country, expected):
    f = extract_transaction_features(tx(), [], account_country_at_event=country).as_dict()
    assert f['account_country_mismatch'] == expected
