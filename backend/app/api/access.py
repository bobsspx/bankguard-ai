from fastapi import APIRouter, Depends

from app.api.dependencies import require_permission
from app.models.staff_user import StaffUser


router = APIRouter(
    prefix="/api/v1/access",
    tags=["authorization"],
)


@router.get("/admin")
def admin_access(
    user: StaffUser = Depends(
        require_permission("staff.manage")
    ),
):
    return {
        "status": "allowed",
        "role": user.role,
        "permission": "staff.manage",
    }


@router.get("/fraud")
def fraud_access(
    user: StaffUser = Depends(
        require_permission("fraud.review")
    ),
):
    return {
        "status": "allowed",
        "role": user.role,
        "permission": "fraud.review",
    }


@router.get("/security")
def security_access(
    user: StaffUser = Depends(
        require_permission(
            "security.monitor"
        )
    ),
):
    return {
        "status": "allowed",
        "role": user.role,
        "permission": "security.monitor",
    }


@router.get("/review")
def review_access(
    user: StaffUser = Depends(
        require_permission("cases.read")
    ),
):
    return {
        "status": "allowed",
        "role": user.role,
        "permission": "cases.read",
    }