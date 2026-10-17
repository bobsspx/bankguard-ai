# Phase 5F.2 Step 1: reproducible synthetic dataset

## Verified status
Phase 5F.1 live smoke check succeeded in the user's screenshot: 94 tests passed,
transaction-features-v1 JSON, all 20 features, history_count_30d=14.
This is a smoke check, not independent validation of all production data.
New full suite: 101 passed (94 existing + 7 new). Python 3.12.
Tests used DATABASE_URL=sqlite:// for existing settings initialization.
New dataset CLI requires no database configuration or new dependencies.

## Install
Copy these NEW files into the existing repository:
- backend/app/ml/build_dataset.py
- backend/tests/test_ml_dataset.py
Do not replace the backend folder. Keep all previous patches.
The sample_dataset directory contains generated demo data only; it need not be
copied into the backend. No migration, API, rule score or database write is added.

## Run in PowerShell
From backend, with .venv activated:

```powershell
python -m pytest -q tests/test_ml_dataset.py
python -m pytest -q
python -m app.ml.build_dataset --output artifacts/phase5f2-seed42 --seed 42 --count 3000 --accounts 30
Get-Content artifacts/phase5f2-seed42/manifest.json
```
Expected: 7 passed, 101 passed, then a JSON export summary.
Output must be a NEW directory. Existing output is rejected to preserve snapshots.
For another run, choose a new --output path. Never overwrite the previous dataset.
The supplied sample uses the same command arguments.

## Output contract
train.jsonl: 2100 rows (1775 label 0, 325 label 1)
validation.jsonl: 450 rows (392 label 0, 58 label 1)
test.jsonl: 450 rows (383 label 0, 67 label 1)
manifest.json: versions, seed, feature names/source hash, split boundaries,
row counts, label counts, class availability, SHA-256 per JSONL file, limitations.
Identical parameters and source/runtime produce byte-identical output, tested.
Feature source hash may differ with line-ending conversion across operating systems.

Each row nests exactly the 20 model inputs in features. transaction_id,
account_id, occurred_at, split, label and label_source are metadata, NOT inputs.
Label 1 denotes a synthetic fraud scenario, 0 a synthetic benign scenario.
Labels are sampled first, then observations are generated with overlapping
amount/device distributions; they are not copied from the Rule Engine or decisions.
Identifiers and dates are synthetic, not customer data.

## Leakage and evaluation contract
Global chronological split 70/15/15; no shuffling or duplicate transaction IDs.
Features use only earlier transactions available at each target time, filtered
by the existing extractor. Historical observations can cross split boundaries,
including earlier validation/test transactions, matching sequential scoring.
No earlier labels are supplied to the feature extractor.
The same accounts appear across splits: this evaluates future events for known
accounts, not generalization to unseen accounts. No warmup period is simulated;
early rows have less history. account_country_mismatch remains null.
The current generator uses immediate arrival and does not simulate delayed ingestion.
Large exports are not optimized: start with the default 3000 rows.

## Next step
Dataset construction is implemented and locally verified. Before baseline
training, verify the commands in the target environment. Fit preprocessing only
on train; tune threshold on validation; reserve test for final evaluation.
Exclude metadata/labels from inputs and handle the all-null country mismatch
column explicitly. Report PR-AUC, precision/recall and confusion matrix against a
simple baseline. Treat any resulting metrics as synthetic benchmark results only.
No trained model, deployment or production accuracy claim is included here.
