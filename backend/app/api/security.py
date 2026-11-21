
"""Security monitoring and audited triage API."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.models.alert import Alert
from app.models.login_event import LoginEvent
from app.models.staff_user import StaffUser
from app.models.security_alert_evidence import SecurityAlertEvidence
from app.services.security_alert_identity import SUPPORTED_SECURITY_RULES

from datetime import datetime
from uuid import UUID
from fastapi import HTTPException
from fastapi import Query
from pydantic import BaseModel, Field
from pydantic import field_validator
from typing import Literal
from sqlalchemy.exc import SQLAlchemyError
from app.models.audit_log import AuditLog
from app.services.alert_triage import AlertNotFoundError, InvalidAlertTransitionError
from app.services.security_triage import read_security_alert, transition_security_alert


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
            Alert.alert_type.in_(sorted(SUPPORTED_SECURITY_RULES)),
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


class SecurityAlertDetail(SecurityAlertItem):
    resolved_at: datetime | None = None


def alert_detail(alert: Alert) -> SecurityAlertDetail:
    return SecurityAlertDetail.model_validate(alert, from_attributes=True)


@router.get("/alerts/{alert_id}", response_model=SecurityAlertDetail)
def get_security_alert(
    alert_id: UUID, db: Session = Depends(get_db),
    _user: StaffUser = Depends(require_permission("security.monitor")),
):
    try:
        return alert_detail(read_security_alert(db, alert_id))
    except AlertNotFoundError:
        raise HTTPException(status_code=404, detail="Security alert not found")


class SecurityTriageRequest(BaseModel):
    status: Literal["investigating", "resolved", "dismissed"]
    expected_status: Literal["open", "investigating", "resolved", "dismissed"]
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("A meaningful reason is required")
        return value


@router.patch("/alerts/{alert_id}", response_model=SecurityAlertDetail)
def triage_security_alert(
    alert_id: UUID, payload: SecurityTriageRequest,
    db: Session = Depends(get_db),
    user: StaffUser = Depends(require_permission("alerts.manage")),
    _monitor: StaffUser = Depends(require_permission("security.monitor")),
):
    try:
        alert = transition_security_alert(
            db, alert_id=alert_id, status=payload.status,
            expected_status=payload.expected_status, reason=payload.reason,
            actor_ref=user.email,
        )
        # Build response before committing so serialization cannot fail after a
        # successful write; both the ORM change and audit flush in this commit.
        result = alert_detail(alert)
        db.commit()
        return result
    except AlertNotFoundError:
        db.rollback()
        raise HTTPException(status_code=404, detail="Security alert not found")
    except InvalidAlertTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Unable to save alert; refresh before retrying")
    except Exception:
        db.rollback()
        raise


class SecurityAuditItem(BaseModel):
    id: UUID
    action: str
    created_at: datetime
    previous_status: str | None = None
    new_status: str | None = None
    reason: str | None = None


class SecurityAuditPage(BaseModel):
    items: list[SecurityAuditItem]
    limit: int
    offset: int
    has_more: bool


@router.get("/alerts/{alert_id}/history", response_model=SecurityAuditPage)
def security_alert_history(
    alert_id: UUID, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: StaffUser = Depends(require_permission("audit.read")),
    _monitor: StaffUser = Depends(require_permission("security.monitor")),
):
    try:
        read_security_alert(db, alert_id)
    except AlertNotFoundError:
        raise HTTPException(status_code=404, detail="Security alert not found")
    rows = db.scalars(select(AuditLog).where(
        AuditLog.resource_type == "alert", AuditLog.resource_id == str(alert_id),
    ).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit + 1).offset(offset)).all()
    items = []
    for row in rows[:limit]:
        details = row.details or {}
        # Deliberately omit actor emails, IP addresses and unrelated audit data.
        items.append(SecurityAuditItem(
            id=row.id, action=row.action, created_at=row.created_at,
            previous_status=details.get("previous_status"), new_status=details.get("new_status"),
            reason=details.get("reason") or details.get("note"),
        ))
    return SecurityAuditPage(items=items, limit=limit, offset=offset, has_more=len(rows) > limit)
