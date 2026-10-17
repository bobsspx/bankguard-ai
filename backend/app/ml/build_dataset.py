"""Reproducible synthetic benchmark; no database access or production labels."""
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import inspect
import json
from pathlib import Path
import random
import shutil
import tempfile
from uuid import UUID

from app.services import ml_features

GENERATOR_VERSION = 'synthetic-transactions-v1'
START = datetime(2025, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Event:
    id: UUID
    account_id: UUID
    device_id: UUID | None
    amount: Decimal
    currency: str
    transaction_type: str
    merchant_category: str | None
    country_code: str
    channel: str
    ip_address: str | None
    occurred_at: datetime
    created_at: datetime


def build_rows(*, seed=42, count=3000, accounts=30):
    if count < 100 or accounts < 1 or accounts > count:
        raise ValueError('Require count >= 100 and 1 <= accounts <= count')
    rng = random.Random(seed)
    history = defaultdict(list)
    rows = []
    for index in range(count):
        account = rng.randrange(accounts)
        # Latent scenario label sampled BEFORE observations; not a rule-engine verdict.
        fraud = int(rng.random() < 0.15)
        unusual_device = rng.random() < (0.60 if fraud else 0.12)
        amount = Decimal(rng.randint(100, 180000 if fraud else 100000)) / 100
        when = START + timedelta(seconds=index * 60 * 86400 // count)
        event = Event(
            id=UUID(int=index + 1), account_id=UUID(int=10_000_000 + account),
            device_id=None if rng.random() < 0.04 else UUID(
                int=20_000_000 + (accounts + index if unusual_device else account)),
            amount=amount, currency=rng.choice(['USD', 'USD', 'THB']),
            transaction_type=rng.choice(['transfer', 'payment']),
            merchant_category=rng.choice(['general', 'retail', 'travel']),
            country_code=rng.choice(['TH', 'TH', 'LA', 'US']),
            channel=rng.choice(['mobile', 'web', 'atm']),
            ip_address=None if rng.random() < 0.03 else f'192.0.2.{rng.randint(1, 254) if unusual_device else account % 254 + 1}',
            occurred_at=when, created_at=when,
        )
        prior = history[event.account_id]
        features = ml_features.extract_transaction_features(event, prior)
        split = 'train' if index < count * 70 // 100 else (
            'validation' if index < count * 85 // 100 else 'test')
        rows.append(dict(transaction_id=str(event.id), account_id=str(event.account_id),
                         occurred_at=when.isoformat(), split=split, label=fraud,
                         label_source='synthetic_latent_scenario', features=features.as_dict()))
        prior.append(event)
        history[event.account_id] = [p for p in prior if p.occurred_at >= when - timedelta(days=30)]
    return rows


def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def export_dataset(output, *, seed=42, count=3000, accounts=30):
    output = Path(output)
    if output.exists():
        raise FileExistsError('Output already exists; choose a new directory')
    rows = build_rows(seed=seed, count=count, accounts=accounts)
    manifest = dict(dataset_version=GENERATOR_VERSION, feature_version=ml_features.FEATURE_VERSION,
                    feature_names=list(ml_features.FEATURE_NAMES), seed=seed, count=count, accounts=accounts,
                    feature_source_sha256=hashlib.sha256(Path(inspect.getfile(ml_features)).read_bytes()).hexdigest(),
                    label_source='synthetic_latent_scenario', split_policy='global chronological 70/15/15',
                    history_policy='Only earlier observable events; prior splits may supply history, never labels',
                    limitations=['Synthetic benchmark only; not evidence of real fraud accuracy',
                                 'Same accounts can occur across time splits; not an unseen-account benchmark',
                                 'No warmup period; early history is incomplete',
                                 'Country snapshot unavailable; feature remains null'], splits={})
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.dataset-', dir=output.parent))
    try:
        for split in ('train', 'validation', 'test'):
            subset = [r for r in rows if r['split'] == split]
            payload = ''.join(encode(r) + '\n' for r in subset).encode('utf-8')
            (temporary / f'{split}.jsonl').write_bytes(payload)
            counts = Counter(r['label'] for r in subset)
            manifest['splits'][split] = dict(rows=len(subset), label_counts=dict(counts),
                start=subset[0]['occurred_at'], end=subset[-1]['occurred_at'],
                sha256=hashlib.sha256(payload).hexdigest(),
                has_both_classes=len(counts) == 2)
        (temporary / 'manifest.json').write_text(encode(manifest) + '\n', encoding='utf-8')
        if output.exists():
            raise FileExistsError('Output appeared during generation; refusing overwrite')
        temporary.rename(output)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--count', type=int, default=3000)
    parser.add_argument('--accounts', type=int, default=30)
    args = parser.parse_args(argv)
    try:
        result = export_dataset(args.output, seed=args.seed, count=args.count, accounts=args.accounts)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Dataset export failed: {exc}\n')
    print(json.dumps({'output': str(args.output), 'splits': result['splits']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
