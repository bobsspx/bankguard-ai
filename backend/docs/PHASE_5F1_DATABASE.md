# Phase 5F.1 — Database adapter

✅ COMPLETED: implementation + local tests (85 passed).
❌ FIX REQUIRED: live PostgreSQL/Neon smoke check pending; not yet full Phase signoff.

## Install
Copy the three complete NEW Python files from this patch into your project:
- backend/app/services/ml_feature_store.py
- backend/app/ml/inspect_features.py
- backend/tests/test_ml_feature_store.py
Place this document under docs/PHASE_5F1_DATABASE.md.
No existing file is replaced. Keep ml_features.py and all 77 existing tests.
No migration, dependency change, API route or frontend modification.

## What it does
load_transaction_features(db, transaction_id) reads persisted Transaction columns,
constructs frozen snapshots and calls the existing extractor. No cached ORM entity
or current Account/Device profile is used. History is restricted in SQL to the same
account, a 30-day inclusive lower bound and exclusive target event timestamp.
Target itself, future events, equal timestamps, and records arriving after the
target's created_at are excluded. Currency filtering for amount aggregates stays
in the existing extractor; counts and device/IP history include all currencies.
No LIMIT: truncated history would silently produce incorrect features.

The service rejects sessions with pending new/dirty/deleted entities and disables
autoflush. It never commits, flushes, rolls back, or closes the caller's session.
Projected columns bypass potentially stale ORM identity-map entities.
Callers should use a fresh REPEATABLE READ transaction for consistent two-query
reads; the CLI explicitly establishes that isolation and SET TRANSACTION READ ONLY.
No HTTP endpoint exposes this internal service, so no new API permission is added.
CLI use requires the developer/operator's existing database access.

## Local evidence and limits
Full suite: 85 passed (77 existing + 8 new), Python 3.12.
SQLAlchemy 2.1.4, pytest 9.1.1, pydantic-settings 2.16.0 were used locally;
these differ from requirements.txt (2.1.1 / 8.4.2 / 2.15.0 respectively).
The user's dependency file was not modified. Confirm with that pinned environment.
Tests use mocked service sessions and real SQLite SQL execution for filtering.
PostgreSQL SQL compilation was also exercised, but no live Neon connection was used.
SQLite is NOT an alternative production backend: it does not preserve the timezone
contract required by feature extraction. The CLI targets PostgreSQL only.
Full tests used DATABASE_URL=sqlite:// solely to satisfy Settings initialization;
no user credentials or external database were accessed.
CLI --help also succeeded without database configuration.

## Windows PowerShell verification

```powershell
cd C:\Users\MSII\Desktop\porfolio\bankguard-ai\backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q tests/test_ml_feature_store.py
python -m pytest -q
```
Expected: 8 passed, then 85 passed.
No alembic upgrade is needed. Previous 0bed84b6e331 (head) is unchanged.

In your PostgreSQL SQL editor, use this READ-ONLY query to choose an existing
synthetic transaction with prior history:

```sql
SELECT t.id, t.transaction_ref
FROM transactions AS t
WHERE EXISTS (
    SELECT 1
    FROM transactions AS h
    WHERE h.account_id = t.account_id
      AND h.id <> t.id
      AND h.occurred_at >= t.occurred_at - INTERVAL '30 days'
      AND h.occurred_at < t.occurred_at
      AND h.created_at <= t.created_at
)
ORDER BY t.occurred_at DESC
LIMIT 5;
```

If no rows match, select any synthetic transaction ID; history_count_30d=0 may be
correct. Do not fabricate history or change timestamps to force nonzero features.

Run the CLI with one returned UUID (not transaction_ref):

```powershell
$transactionId = Read-Host "Paste transaction UUID"
python -m app.ml.inspect_features $transactionId
```

The CLI reads your existing .env through the existing app.db.session configuration.
Do not paste DATABASE_URL or secrets into chat. Expected JSON contains
transaction_id, feature_version=transaction-features-v1 and 20 feature values.
account_country_mismatch=null is intentional: no historical account-country
snapshot exists. Null mean/ratio/novelty is valid when history is unavailable.
Missing ID exits 2; database/data errors exit 1. Successful output exits 0.

## Verify amount/count independently (optional, if output is unexpected)
Replace the UUID placeholder with the same selected UUID:

```sql
SELECT count(h.id) AS history_count_30d,
       count(h.id) FILTER (
           WHERE h.occurred_at >= t.occurred_at - INTERVAL '10 minutes'
       ) AS recent_count_10m,
       avg(h.amount) FILTER (WHERE upper(h.currency) = upper(t.currency)) AS mean_amount_30d
FROM transactions t
LEFT JOIN transactions h
    ON h.account_id = t.account_id AND h.id <> t.id
   AND h.occurred_at >= t.occurred_at - INTERVAL '30 days'
   AND h.occurred_at < t.occurred_at
   AND h.created_at <= t.created_at
WHERE t.id = 'REPLACE_WITH_TRANSACTION_UUID'::uuid
GROUP BY t.id;
```

## Return 3 screenshots
1. New tests and full test summary (8 and 85 passed).
2. SQL selection with chosen synthetic transaction UUID.
3. CLI JSON output for that UUID (whole output if possible).

## Historical-data caveats
This reads current stored transaction fields. The schema does not version edits;
REPEATABLE READ stabilizes this read, not historical truth. created_at is a proxy
for availability, and the CLI cannot prove historical point-in-time correctness.
For training, preserve immutable dataset snapshots and disclose backfill/edit
limitations. Bulk seeding with identical created_at can also limit fidelity.
This implementation is for the current portfolio dataset, loading a full 30-day
account window into memory. Large-scale export needs separate batch optimization.

## Next gate
Once live smoke output and local 85 tests pass, close 5F.1 and proceed to 5F.2:
reproducible synthetic labels, dataset metadata and chronological split. No labels
or model training have been added in this patch.
