import hashlib
import json

import pytest

from app.ml.build_dataset import build_rows, export_dataset
from app.services.ml_features import FEATURE_NAMES


def test_seed_reproduces_and_changes_data():
    assert build_rows(count=100) == build_rows(count=100)
    assert build_rows(count=100) != build_rows(count=100, seed=43)


def test_chronological_disjoint_splits_and_feature_allowlist():
    rows = build_rows(count=100)
    assert len({r['transaction_id'] for r in rows}) == 100
    assert [r['occurred_at'] for r in rows] == sorted(r['occurred_at'] for r in rows)
    assert [sum(r['split'] == s for r in rows) for s in ['train', 'validation', 'test']] == [70, 15, 15]
    for row in rows:
        assert tuple(row['features']) == FEATURE_NAMES
        assert row['label'] in (0, 1)
        assert row['features']['account_country_mismatch'] is None
        assert row['label_source'] == 'synthetic_latent_scenario'


def test_history_crosses_split_boundary_without_current_or_future_events():
    rows = build_rows(count=100, accounts=1)
    assert rows[0]['features']['history_count_30d'] == 0
    assert rows[1]['features']['history_count_30d'] == 1
    assert rows[70]['features']['history_count_30d'] == 50


@pytest.mark.parametrize('kwargs', [{'count': 99}, {'accounts': 0}, {'count': 100, 'accounts': 101}])
def test_invalid_parameters(kwargs):
    with pytest.raises(ValueError):
        build_rows(**kwargs)


def test_export_checksums_reproducibility_and_no_overwrite(tmp_path):
    first, second = tmp_path / 'first', tmp_path / 'second'
    manifest = export_dataset(first, count=100)
    export_dataset(second, count=100)
    for path in first.iterdir():
        assert path.read_bytes() == (second / path.name).read_bytes()
    for name, details in manifest['splits'].items():
        payload = (first / f'{name}.jsonl').read_bytes()
        assert hashlib.sha256(payload).hexdigest() == details['sha256']
        assert len([json.loads(line) for line in payload.splitlines()]) == details['rows']
    with pytest.raises(FileExistsError):
        export_dataset(first, count=100)
    assert json.loads((first / 'manifest.json').read_text())['count'] == 100
