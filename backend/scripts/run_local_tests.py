"""Run local tests without dotenv files or PostgreSQL connections.

Usage from backend: .venv/Scripts/python.exe scripts/run_local_tests.py
Optional pytest arguments replace the default `tests -q`.
This runner does not verify live PostgreSQL behavior.
"""
import os
from pathlib import Path
import sys
from unittest.mock import patch


def main() -> int:
    backend = Path(__file__).resolve().parents[1]
    os.chdir(backend)
    sys.path.insert(0, str(backend))
    os.environ.update(
        APP_ENV="test", DATABASE_URL="sqlite:///:memory:",
        JWT_SECRET="bankguard-local-test-key-not-a-secret",
    )
    from pydantic_settings.sources import DotEnvSettingsSource
    import pytest

    with patch.object(DotEnvSettingsSource, "_read_env_files", return_value={}), patch(
        "psycopg.connect", side_effect=AssertionError("PostgreSQL disabled during local tests"),
    ):
        return pytest.main(sys.argv[1:] or ["tests", "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
