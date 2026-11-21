from scripts.run_ci_postgres import is_ci_target
from app.schemas.auth import CurrentUserResponse
from uuid import uuid4


def test_ci_postgres_runner_rejects_shared_or_unmarked_databases():
    local = "postgresql+psycopg://bankguard_ci:placeholder@127.0.0.1:5432/bankguard_ci"
    assert is_ci_target(local, "1")
    assert not is_ci_target(local, None)
    assert not is_ci_target(local.replace("127.0.0.1", "example.neon.tech"), "1")
    assert not is_ci_target(local.replace("/bankguard_ci", "/neondb"), "1")
    assert not is_ci_target(local.replace("bankguard_ci:placeholder", "postgres:placeholder"), "1")
    assert not is_ci_target(local + "?connect_timeout=5", "1")
    assert not is_ci_target(local.replace(":5432", ":invalid"), "1")


def test_browser_fixture_email_is_accepted_by_auth_response():
    response = CurrentUserResponse(
        id=uuid4(), email="ci-synthetic@bankguard.demo", role="fraud_analyst", permissions=[],
    )
    assert response.email == "ci-synthetic@bankguard.demo"
