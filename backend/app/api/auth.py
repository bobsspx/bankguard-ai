from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import update
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
from app.services.audit import write_audit_log
from app.services.login_rate_limit import reserve_login_attempt
from sqlalchemy.exc import SQLAlchemyError


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["authentication"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    try:
        retry_after = reserve_login_attempt(
            db, email=form_data.username,
            client_ip=request.client.host if request.client else "unknown",
        )
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Authentication service unavailable.")
    if retry_after is not None:
        raise HTTPException(
            status_code=429, detail="Too many login attempts.",
            headers={"Retry-After": str(retry_after)},
        )
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


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
    user: StaffUser = Depends(get_current_staff_user),
):
    result = db.execute(
        update(StaffUser)
        .where(StaffUser.id == user.id, StaffUser.session_version == user.session_version)
        .values(session_version=StaffUser.session_version + 1)
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token.")

    write_audit_log(
        db, actor_ref=user.email, action="AUTH_LOGOUT",
        resource_type="staff_user", resource_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return {"status": "ok"}


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
