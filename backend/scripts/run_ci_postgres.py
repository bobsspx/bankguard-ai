"""Migrate and test only a disposable, local CI PostgreSQL database."""

import os
from pathlib import Path
import sys
from unittest.mock import patch
from urllib.parse import urlparse


def is_ci_target(url: str, enabled: str | None) -> bool:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError:
        return False
    return (
        enabled == "1"
        and parsed.scheme == "postgresql+psycopg"
        and parsed.hostname == "127.0.0.1"
        and port == 5432
        and parsed.path == "/bankguard_ci"
        and parsed.username == "bankguard_ci"
        and not parsed.query
        and not parsed.fragment
    )


def main() -> int:
    if not is_ci_target(os.environ.get("DATABASE_URL", ""), os.environ.get("CI_POSTGRES_TEST")):
        raise SystemExit("Disposable local CI PostgreSQL target required")
    if os.environ.get("APP_ENV") != "test":
        raise SystemExit("APP_ENV=test required")

    backend = Path(__file__).resolve().parents[1]
    os.chdir(backend)
    sys.path.insert(0, str(backend))
    from pydantic_settings.sources import DotEnvSettingsSource
    from alembic import command
    from alembic.config import Config
    import pytest

    with patch.object(DotEnvSettingsSource, "_read_env_files", return_value={}):
        command.upgrade(Config(str(backend / "alembic.ini")), "head")
        return pytest.main(["integration_tests/test_ci_postgres.py", "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
