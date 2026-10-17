"""Train a synthetic-only baseline; validation selects threshold, test only evaluates."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform
import shutil
import tempfile
import warnings

from app.ml.baseline import MODEL_VERSION, vector_record, predict
from app.services.ml_features import FEATURE_NAMES, FEATURE_VERSION


def read_dataset(directory):
    directory = Path(directory)
    manifest_bytes = (directory / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    if (manifest.get('feature_version') != FEATURE_VERSION or
        manifest.get('feature_names') != list(FEATURE_NAMES) or
        manifest.get('label_source') != 'synthetic_latent_scenario'):
        raise ValueError('Unsupported dataset contract')
    result, seen, previous = {}, set(), None
    for split in ('train', 'validation', 'test'):
        raw = (directory / (split + '.jsonl')).read_bytes()
        details = manifest['splits'][split]
        if hashlib.sha256(raw).hexdigest() != details['sha256']:
            raise ValueError('Dataset checksum mismatch: ' + split)
        rows = [json.loads(line) for line in raw.splitlines()]
        if len(rows) != details['rows'] or not rows:
            raise ValueError('Dataset row count mismatch')
        for row in rows:
            if (row['split'] != split or row['label_source'] != 'synthetic_latent_scenario'
                or type(row['label']) is not int or row['label'] not in (0, 1)):
                raise ValueError('Invalid label/split contract')
            if row['transaction_id'] in seen:
                raise ValueError('Duplicate transaction across splits')
            seen.add(row['transaction_id'])
            when = datetime.fromisoformat(row['occurred_at'])
            if when.utcoffset() is None or (previous is not None and when <= previous):
                raise ValueError('Dataset must be strictly chronological')
            previous = when
            vector_record(row['features'])
        counts = Counter(r['label'] for r in rows)
        if set(counts) != {0, 1}:
            raise ValueError('Each split requires both classes')
        if {str(k): v for k, v in counts.items()} != details['label_counts']:
            raise ValueError('Dataset label count mismatch')
        result[split] = rows
    return result, hashlib.sha256(manifest_bytes).hexdigest()


def metrics(y, probabilities, threshold):
    from sklearn.metrics import average_precision_score, roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix
    predicted = [int(p >= threshold) for p in probabilities]
    return dict(average_precision=float(average_precision_score(y, probabilities)),
                roc_auc=float(roc_auc_score(y, probabilities)),
                precision=float(precision_score(y, predicted, zero_division=0)),
                recall=float(recall_score(y, predicted, zero_division=0)),
                f1=float(f1_score(y, predicted, zero_division=0)),
                confusion_matrix=confusion_matrix(y, predicted, labels=[0, 1]).tolist())


def train(dataset, output):
    import numpy as np
    import sklearn
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression
    from sklearn.exceptions import ConvergenceWarning

    output = Path(output)
    if output.exists():
        raise FileExistsError('Choose a new output directory')
    rows, manifest_hash = read_dataset(dataset)
    vectorizer = DictVectorizer(sparse=True)
    scaler = StandardScaler(with_mean=False)
    records = {s: [vector_record(r['features']) for r in items] for s, items in rows.items()}
    labels = {s: [r['label'] for r in items] for s, items in rows.items()}
    xtrain = scaler.fit_transform(vectorizer.fit_transform(records['train']))
    estimator = LogisticRegression(C=1.0, max_iter=3000, random_state=42, solver='lbfgs')
    with warnings.catch_warnings():
        warnings.simplefilter('error', ConvergenceWarning)
        estimator.fit(xtrain, labels['train'])
    validation = estimator.predict_proba(scaler.transform(vectorizer.transform(records['validation'])))[:, 1]
    # Fixed grid and tie rule, chosen solely on validation F1. No test-based selection.
    threshold = max([i / 100 for i in range(5, 96)],
                    key=lambda t: (metrics(labels['validation'], validation, t)['f1'], t))
    model = dict(model_version=MODEL_VERSION, feature_version=FEATURE_VERSION,
                 feature_names=list(FEATURE_NAMES), training_source='synthetic_latent_scenario',
                 threshold=threshold, intercept=float(estimator.intercept_[0]),
                 weights=dict(zip(vectorizer.get_feature_names_out().tolist(),
                                  (estimator.coef_[0] / scaler.scale_).tolist())),
                 dataset_manifest_sha256=manifest_hash)
    report = dict(model_version=MODEL_VERSION, dataset_manifest_sha256=manifest_hash,
                  runtime=dict(python=platform.python_version(), sklearn=sklearn.__version__, numpy=np.__version__),
                  threshold=threshold, threshold_policy='validation F1 over 0.05..0.95 step 0.01, ties prefer higher',
                  preprocessing='Train-only DictVectorizer + StandardScaler; numeric null=0 plus missing indicator',
                  limitation='Synthetic benchmark only. Score is not calibrated real-world fraud probability.',
                  confusion_matrix_order='[[TN, FP], [FN, TP]]', splits={})
    prevalence = sum(labels['train']) / len(labels['train'])
    for split in ('validation', 'test'):
        sklearn_probs = estimator.predict_proba(scaler.transform(vectorizer.transform(records[split])))[:, 1]
        portable_probs = [predict(model, row['features']) for row in rows[split]]
        if not np.allclose(sklearn_probs, portable_probs, atol=1e-10, rtol=0):
            raise ValueError('Portable inference parity failed')
        report['splits'][split] = dict(rows=len(rows[split]), model=metrics(labels[split], portable_probs, threshold),
            constant_baseline=metrics(labels[split], [prevalence] * len(rows[split]), 0.5))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.training-', dir=output.parent))
    try:
        model_bytes = (json.dumps(model, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
        (temporary / 'baseline.json').write_bytes(model_bytes)
        report['model_sha256'] = hashlib.sha256(model_bytes).hexdigest()
        (temporary / 'metrics.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        if output.exists():
            raise FileExistsError('Output appeared during training')
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = train(args.dataset, args.output)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'Training failed: {exc}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
