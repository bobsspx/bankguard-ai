from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_staff_user,
)
from app.core.rbac import permissions_for_role
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.staff_user import StaffUser
from app.schemas.auth import (
    CurrentUserResponse,
    TokenResponse,
)
from app.services.auth import authenticate_staff_user


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_staff_user(
        db,
        email=form_data.username,
        password=form_data.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
        session_version=user.session_version,
    )

    return TokenResponse(
        access_token=token,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
def current_user(
    user: StaffUser = Depends(
        get_current_staff_user
    ),
):
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        permissions=permissions_for_role(
            user.role
        ),
    )