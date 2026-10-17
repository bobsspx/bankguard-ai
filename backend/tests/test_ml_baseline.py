import json
import math
from pathlib import Path

import pytest

from app.ml.baseline import load_model, predict, vector_record
from app.ml.build_dataset import build_rows, export_dataset
from app.ml.train_baseline import read_dataset, train


def test_portable_model_handles_unknown_categories_and_nulls():
    model = load_model()
    features = build_rows(count=100)[0]['features']
    features['channel'] = 'new-channel'
    features['mean_amount_30d'] = None
    assert 0 <= predict(model, features) <= 1
    assert vector_record(features)['mean_amount_30d__missing'] == 1
    assert 'label' not in vector_record(features)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), 'invalid', True])
def test_invalid_numeric_feature_rejected(bad):
    features = build_rows(count=100)[0]['features']
    features['amount'] = bad
    with pytest.raises(ValueError):
        predict(load_model(), features)


def test_extra_metadata_cannot_enter_model():
    features = build_rows(count=100)[0]['features']
    features['label'] = 1
    with pytest.raises(ValueError):
        vector_record(features)


def test_incompatible_model_rejected(tmp_path):
    model = load_model()
    model['feature_version'] = 'wrong'
    path = tmp_path / 'bad.json'
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError):
        load_model(path)


def test_dataset_tampering_rejected(tmp_path):
    export_dataset(tmp_path / 'data', count=100)
    path = tmp_path / 'data/train.jsonl'
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='checksum'):
        read_dataset(tmp_path / 'data')


def test_training_export_parity_and_model_independent_of_test_labels(tmp_path):
    import hashlib
    from collections import Counter
    dataset = tmp_path / 'data'
    export_dataset(dataset, count=1000)
    first = train(dataset, tmp_path / 'run1')
    # Alter only held-out test labels with valid metadata: fitted model/threshold must not change.
    path = dataset / 'test.jsonl'
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    for row in rows:
        row['label'] = 1 - row['label']
    payload = ''.join(json.dumps(row) + '\n' for row in rows).encode()
    path.write_bytes(payload)
    manifest_path = dataset / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['splits']['test']['sha256'] = hashlib.sha256(payload).hexdigest()
    manifest['splits']['test']['label_counts'] = dict(Counter(r['label'] for r in rows))
    manifest_path.write_text(json.dumps(manifest))
    train(dataset, tmp_path / 'run2')
    m1, m2 = load_model(tmp_path / 'run1/baseline.json'), load_model(tmp_path / 'run2/baseline.json')
    for key in ['weights', 'intercept', 'threshold']:
        assert m1[key] == m2[key]
    assert math.isfinite(first['splits']['test']['model']['average_precision'])
    with pytest.raises(FileExistsError):
        train(dataset, tmp_path / 'run1')
