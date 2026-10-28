
"""Read-only Security Monitoring API."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.alert import Alert
from app.models.login_event import LoginEvent
from app.models.staff_user import StaffUser
from app.models.security_alert_evidence import SecurityAlertEvidence

from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel, Field


router = APIRouter(
    prefix="/api/v1/security",
    tags=["security-monitoring"],
)


@router.get("/summary")
def security_summary(
    db: Session = Depends(get_db),
    _user: StaffUser = Depends(
        require_permission("security.monitor")
    ),
):
    total_logins = db.scalar(
        select(func.count(LoginEvent.id))
    ) or 0

    failed_logins = db.scalar(
        select(func.count(LoginEvent.id)).where(
            LoginEvent.success.is_(False)
        )
    ) or 0

    security_alerts = db.scalar(
        select(func.count(Alert.id)).where(
            Alert.login_event_id.is_not(None)
        )
    ) or 0

    open_security_alerts = db.scalar(
        select(func.count(Alert.id)).where(
            Alert.login_event_id.is_not(None),
            Alert.status == "open",
        )
    ) or 0

    return {
        "total_login_events": total_logins,
        "failed_login_events": failed_logins,
        "security_alerts": security_alerts,
        "open_security_alerts": open_security_alerts,
    }


class SecurityAlertItem(BaseModel):
    id: UUID
    login_event_id: UUID
    alert_type: str
    severity: str
    status: str
    title: str
    description: str
    created_at: datetime
    


class SecurityAlertPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[SecurityAlertItem] = Field(default_factory=list)


@router.get("/alerts", response_model=SecurityAlertPage)
def list_security_alerts(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: StaffUser = Depends(
        require_permission("security.monitor")
    ),
):
    from app.models.security_alert_evidence import (
        SecurityAlertEvidence,
    )

    conditions = [
        Alert.login_event_id.is_not(None),
    ]

    if status is not None:
        if status not in {
            "open", "investigating",
            "resolved", "dismissed",
        }:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail="Invalid alert status",
            )
        conditions.append(Alert.status == status)

    total = db.scalar(
        select(func.count(Alert.id)).where(*conditions)
    ) or 0

    statement = (
        select(
            Alert.id,
            Alert.login_event_id,
            Alert.alert_type,
            Alert.severity,
            Alert.status,
            Alert.title,
            Alert.description,
            Alert.created_at,
            
        )
        .where(*conditions)
        .order_by(
            Alert.created_at.desc(),
            Alert.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(statement).mappings().all()

    return SecurityAlertPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[
            SecurityAlertItem(**dict(row))
            for row in rows
        ],
    )


class SecurityEvidenceResponse(BaseModel):
    alert_id: UUID
    alert_type: str
    evidence: dict


@router.get(
    "/alerts/{alert_id}/evidence",
    response_model=SecurityEvidenceResponse,
)
def read_security_alert_evidence(
    alert_id: UUID,
    db: Session = Depends(get_db),
    _user: StaffUser = Depends(
        require_permission("audit.read")
    ),
):
    statement = (
        select(
            Alert.id.label("alert_id"),
            Alert.alert_type,
            SecurityAlertEvidence.snapshot.label("evidence"),
        )
        .join(
            SecurityAlertEvidence,
            SecurityAlertEvidence.alert_id == Alert.id,
        )
        .where(
            Alert.id == alert_id,
            Alert.alert_type == "FAILED_LOGIN_BURST",
            Alert.login_event_id.is_not(None),
        )
    )

    row = db.execute(statement).mappings().one_or_none()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Security evidence not found",
        )

    return SecurityEvidenceResponse(**dict(row))
