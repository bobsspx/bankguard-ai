# Phase 5F.1 CLI input fix

Evidence: user's screenshot confirms 85 passed. CLI screenshot shows a missing
transaction_id argument, before any database query. Live PostgreSQL check pending.

Install from the repository root (bankguard-ai):
- Replace backend/app/ml/inspect_features.py (back up your existing file first).
- Add backend/tests/test_inspect_features_cli.py.
No migration or dependency change is required.

Local verification: 94 passed (85 existing + 9 input tests).
Tests ran with DATABASE_URL=sqlite:// for settings initialization, not live Neon.
--help works without database settings. This patch changes only input handling.

PowerShell, from backend with your virtual environment activated:

```powershell
python -m pytest -q
python -m app.ml.inspect_features
```

At `Paste transaction UUID:` paste the id returned by the SQL below, then Enter.
Do not paste transaction_ref, SQL, or a PowerShell command into that prompt.

Run this read-only SQL in your database SQL editor to obtain an existing ID:

```sql
SELECT id, transaction_ref
FROM transactions
ORDER BY occurred_at DESC
LIMIT 5;
```

Use a synthetic/demo transaction. An empty result means there are no transactions;
do not invent a UUID. The command still accepts a UUID directly as an argument.
Blank/invalid UUID or a cancelled prompt exits with code 2 before DB access.

Expected successful output: transaction_id, feature_version equal to
transaction-features-v1, and 20 entries under features.
account_country_mismatch=null is expected without a historical country snapshot.
With no earlier history, zero counts and null historical statistics can be valid.
Database reads retain REPEATABLE READ and SET TRANSACTION READ ONLY.

Send the complete resulting JSON (screenshot is fine) to verify live behavior.
Do not send .env or DATABASE_URL. Phase 5F.2 dataset work follows this live gate.
