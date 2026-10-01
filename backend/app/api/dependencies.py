import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac import has_permission
from app.core.security import (
    InvalidTokenError,
    decode_access_token,
)
from app.db.session import get_db
from app.models.staff_user import StaffUser


oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


def get_current_staff_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> StaffUser:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token.",
        headers={
            "WWW-Authenticate": "Bearer",
        },
    )

    try:
        payload = decode_access_token(token)

        user_id = uuid.UUID(
            payload["sub"]
        )

        token_session_version = int(
            payload["sv"]
        )

    except (
        InvalidTokenError,
        KeyError,
        ValueError,
        TypeError,
    ):
        raise credentials_error

    user = db.scalar(
        select(StaffUser).where(
            StaffUser.id == user_id
        )
    )

    if user is None:
        raise credentials_error

    if not user.is_active:
        raise credentials_error

    if (
        user.session_version
        != token_session_version
    ):
        raise credentials_error

    return user


def require_permission(
    permission: str,
):
    def dependency(
        user: StaffUser = Depends(
            get_current_staff_user
        ),
    ) -> StaffUser:
        if not has_permission(
            user.role,
            permission,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        return user

    return dependency