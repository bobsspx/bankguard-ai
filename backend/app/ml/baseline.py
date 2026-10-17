"""Portable JSON logistic model. Runtime inference uses only the standard library."""
import json
import math
from pathlib import Path
from app.services.ml_features import FEATURE_NAMES, FEATURE_VERSION

CATEGORICAL = {'currency', 'channel', 'transaction_type', 'merchant_category', 'country_code'}
MODEL_VERSION = 'synthetic-logistic-v1'
DEFAULT_MODEL = Path(__file__).resolve().parent / 'artifacts' / 'baseline.json'


def vector_record(features):
    if set(features) != set(FEATURE_NAMES):
        raise ValueError('Feature schema mismatch')
    result = {}
    for name in FEATURE_NAMES:
        value = features[name]
        if name in CATEGORICAL:
            if value is not None and not isinstance(value, str):
                raise ValueError('Invalid categorical feature')
            result[name] = value if value is not None else '__missing__'
        else:
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError('Invalid numeric feature')
            result[name] = 0.0 if value is None else float(value)
            result[name + '__missing'] = float(value is None)
    return result


def load_model(path=DEFAULT_MODEL):
    model = json.loads(Path(path).read_text(encoding='utf-8'))
    if (model.get('model_version') != MODEL_VERSION or
        model.get('feature_version') != FEATURE_VERSION or
        model.get('feature_names') != list(FEATURE_NAMES) or
        model.get('training_source') != 'synthetic_latent_scenario'):
        raise ValueError('Unsupported model contract')
    weights = model.get('weights')
    if not isinstance(weights, dict) or not weights:
        raise ValueError('Invalid model weights')
    for key, value in weights.items():
        if not isinstance(key, str) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError('Invalid model weights')
    for name in ('intercept', 'threshold'):
        if not isinstance(model.get(name), (float, int)) or not math.isfinite(model[name]):
            raise ValueError('Invalid model parameter')
    if not 0 <= model['threshold'] <= 1:
        raise ValueError('Invalid model threshold')
    return model


def predict(model, features):
    record = vector_record(features)
    terms = []
    for name, value in record.items():
        key, numeric = (name + '=' + value, 1.0) if isinstance(value, str) else (name, value)
        terms.append(model['weights'].get(key, 0.0) * numeric)
    z = math.fsum([model['intercept'], *terms])
    if not math.isfinite(z):
        raise ValueError('Prediction exceeds numeric range')
    probability = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
    return probability

def find_unseen_categories(model, features):
    record = vector_record(features)

    return [
        f"{name}={record[name]}"
        for name in sorted(CATEGORICAL)
        if f"{name}={record[name]}" not in model["weights"]
    ]