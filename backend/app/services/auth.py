from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    DUMMY_PASSWORD_HASH,
    verify_password,
)
from app.models.staff_user import StaffUser


def authenticate_staff_user(
    db: Session,
    *,
    email: str,
    password: str,
) -> StaffUser | None:
    normalized_email = email.strip().lower()

    user = db.scalar(
        select(StaffUser).where(
            StaffUser.email == normalized_email
        )
    )

    if user is None:
        verify_password(
            password,
            DUMMY_PASSWORD_HASH,
        )
        return None

    if not verify_password(
        password,
        user.password_hash,
    ):
        return None

    if not user.is_active:
        return None

    return user