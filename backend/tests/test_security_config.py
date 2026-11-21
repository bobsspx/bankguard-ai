import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("secret", ["change-me", "short"])
def test_production_rejects_weak_jwt_secret(secret):
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///:memory:", app_env="production",
                 jwt_secret=secret, _env_file=None)


def test_test_environment_allows_explicit_synthetic_secret():
    settings = Settings(database_url="sqlite:///:memory:", app_env="test",
                        jwt_secret="synthetic-test-only-key-that-is-at-least-32-bytes",
                        _env_file=None)
    assert settings.jwt_algorithm == "HS256"


def test_unsupported_jwt_algorithm_is_rejected():
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///:memory:", app_env="test",
                 jwt_secret="synthetic-test-only-key-that-is-at-least-32-bytes",
                 jwt_algorithm="none", _env_file=None)


def test_unknown_environment_cannot_bypass_production_secret_check():
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///:memory:", app_env="prod",
                 jwt_secret="change-me", _env_file=None)


def test_production_accepts_strong_jwt_secret():
    settings = Settings(database_url="sqlite:///:memory:", app_env="production",
                        jwt_secret="synthetic-test-only-key-that-is-at-least-32-bytes",
                        _env_file=None)
    assert settings.app_env == "production"
