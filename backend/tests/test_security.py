from app.core.security import (
    hash_password,
    verify_password,
)


def test_password_hashing():
    password = "ExamplePassword123!"

    hashed = hash_password(password)

    assert hashed != password

    assert verify_password(
        password,
        hashed,
    )


def test_wrong_password_fails():
    hashed = hash_password(
        "CorrectPassword123!"
    )

    assert not verify_password(
        "WrongPassword123!",
        hashed,
    )