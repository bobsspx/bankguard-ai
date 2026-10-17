from uuid import UUID

import pytest

from app.ml.inspect_features import parse_transaction_id


ID = "12345678-1234-5678-1234-567812345678"


def test_explicit_uuid_does_not_prompt(monkeypatch):
    def unexpected(*args):
        pytest.fail("Explicit UUID must not prompt")
    monkeypatch.setattr("builtins.input", unexpected)
    assert parse_transaction_id([ID]) == UUID(ID)


def test_missing_argument_prompts_and_strips_spaces(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: f"  {ID}  ")
    assert parse_transaction_id([]) == UUID(ID)


@pytest.mark.parametrize("value", ["", "   ", "TXN-001", "not-a-uuid"])
def test_invalid_prompt_value_is_usage_error(monkeypatch, capsys, value):
    monkeypatch.setattr("builtins.input", lambda _: value)
    with pytest.raises(SystemExit) as error:
        parse_transaction_id([])
    assert error.value.code == 2
    assert "transactions.id" in capsys.readouterr().err


@pytest.mark.parametrize("exception", [EOFError, KeyboardInterrupt])
def test_cancelled_prompt_exits_cleanly(monkeypatch, capsys, exception):
    def cancel(_):
        raise exception()
    monkeypatch.setattr("builtins.input", cancel)
    with pytest.raises(SystemExit) as error:
        parse_transaction_id([])
    assert error.value.code == 2
    assert "No transaction UUID supplied" in capsys.readouterr().err


def test_invalid_explicit_uuid_is_usage_error():
    with pytest.raises(SystemExit) as error:
        parse_transaction_id(["TXN-001"])
    assert error.value.code == 2
