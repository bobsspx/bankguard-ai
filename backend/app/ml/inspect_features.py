"""Usage: python -m app.ml.inspect_features TRANSACTION_UUID

Uses configured PostgreSQL credentials; prints features, never connection URLs.
"""
import argparse
import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.services.ml_feature_store import (
    FeatureTransactionNotFoundError,
    load_transaction_features,
)


def parse_transaction_id(argv=None) -> UUID:
    parser = argparse.ArgumentParser(description="Inspect persisted transaction ML features")
    parser.add_argument("transaction_id", nargs="?", help="Transaction UUID; prompts if omitted")
    args = parser.parse_args(argv)
    raw = args.transaction_id
    if raw is None:
        try:
            raw = input("Paste transaction UUID: ")
        except (EOFError, KeyboardInterrupt):
            parser.error("No transaction UUID supplied. Pass it as a command-line argument.")
    try:
        return UUID(raw.strip())
    except ValueError:
        parser.error("Enter a valid transaction UUID from transactions.id (not transaction_ref).")


def main(argv=None) -> int:
    transaction_id = parse_transaction_id(argv)
    # Deferred import lets --help work without database configuration.
    from app.db.session import engine

    try:
        with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                with Session(bind=connection, autoflush=False) as db:
                    row = load_transaction_features(db, transaction_id)
                    print(json.dumps({
                        "transaction_id": str(row.transaction_id),
                        "feature_version": row.feature_version,
                        "features": row.as_dict(),
                    }, indent=2, allow_nan=False))
        return 0
    except FeatureTransactionNotFoundError:
        print("Transaction not found.")
        return 2
    except (SQLAlchemyError, ValueError):
        print("Feature inspection failed. Check database access and transaction data.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
