from getpass import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.staff_user import StaffUser


ALLOWED_ROLES = {
    "admin",
    "fraud_analyst",
    "security_analyst",
    "reviewer",
}


def main():
    email = input(
        "Email: "
    ).strip().lower()

    role = input(
        "Role: "
    ).strip().lower()

    if role not in ALLOWED_ROLES:
        raise SystemExit(
            "Invalid role."
        )

    password = getpass(
        "Password: "
    )

    confirmation = getpass(
        "Confirm password: "
    )

    if password != confirmation:
        raise SystemExit(
            "Passwords do not match."
        )

    if len(password) < 12:
        raise SystemExit(
            "Password must contain "
            "at least 12 characters."
        )

    with SessionLocal() as db:
        existing = db.scalar(
            select(StaffUser).where(
                StaffUser.email == email
            )
        )

        if existing:
            raise SystemExit(
                "User already exists."
            )

        user = StaffUser(
            email=email,
            password_hash=hash_password(
                password
            ),
            role=role,
            is_active=True,
        )

        db.add(user)
        db.commit()

        print(
            f"Created {email} "
            f"with role={role}"
        )


if __name__ == "__main__":
    main()