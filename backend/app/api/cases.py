import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from pydantic import ValidationError
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import (
    require_permission,
)
from app.db.session import get_db
from app.models.staff_user import (
    StaffUser,
)
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.fraud_decision import FraudDecision
from app.models.investigation_case import InvestigationCase
from app.models.security_alert_evidence import SecurityAlertEvidence
from app.schemas.case import (
    CaseAuditItem,
    CaseContextResponse,
    CaseEvidenceResponse,
    CaseCreateRequest,
    CaseFilters,
    CasePage,
    CaseResponse,
    CaseUpdateRequest,
)
from app.services.security_alert_identity import SUPPORTED_SECURITY_RULES
from app.services.audit import (
    write_audit_log,
)
from app.services.case_management import (
    CaseAlertNotFoundError,
    CaseAlreadyExistsError,
    CaseNotFoundError,
    InvalidCaseAlertError,
    InvalidCaseAssigneeError,
    InvalidCaseTransitionError,
    StaleCaseStatusError,
    create_case,
    get_case,
    list_cases,
    update_case,
)


router = APIRouter(
    prefix="/api/v1/cases",
    tags=["cases"],
)


def load_case_context(db: Session, case_id: uuid.UUID, limit: int, offset: int):
    case = db.scalar(select(InvestigationCase).where(InvestigationCase.id == case_id))
    if case is None:
        raise CaseNotFoundError
    evidence = db.scalar(
        select(SecurityAlertEvidence.snapshot)
        .join(Alert, Alert.id == SecurityAlertEvidence.alert_id)
        .where(Alert.id == case.alert_id, Alert.login_event_id.is_not(None),
               Alert.alert_type.in_(sorted(SUPPORTED_SECURITY_RULES)))
    )
    decision_id = db.scalar(select(FraudDecision.id).where(FraudDecision.case_id == case_id))
    conditions = [and_(AuditLog.resource_type == "investigation_case",
                       AuditLog.resource_id == str(case_id))]
    if decision_id is not None:
        conditions.append(and_(AuditLog.resource_type == "fraud_decision",
                               AuditLog.resource_id == str(decision_id)))
    rows = db.scalars(
        select(AuditLog).where(or_(*conditions))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit + 1).offset(offset)
    ).all()
    return case_id, evidence, rows[:limit], len(rows) > limit


def build_case_context(case_id, snapshot, rows, has_more) -> CaseContextResponse:
    evidence = None
    if snapshot is not None:
        evidence = CaseEvidenceResponse(**{
            key: snapshot[key] for key in
            ("rule_code", "triggering_event_id", "evidence_event_ids", "event_count")
        })
        if evidence.event_count != len(evidence.evidence_event_ids):
            raise ValueError("Invalid evidence count")
    return CaseContextResponse(
        case_id=case_id, evidence=evidence, has_more=has_more,
        audit=[CaseAuditItem(
            id=row.id, action=row.action, created_at=row.created_at,
            previous_status=(row.details or {}).get("previous_status") or
                            (row.details or {}).get("previous_case_status"),
            new_status=(row.details or {}).get("new_status") or
                       (row.details or {}).get("new_case_status"),
            reason=(row.details or {}).get("reason"),
        ) for row in rows],
    )


@router.get("/{case_id}/context", response_model=CaseContextResponse)
def read_case_context(
    case_id: uuid.UUID, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: StaffUser = Depends(require_permission("cases.read")),
):
    try:
        return build_case_context(*load_case_context(db, case_id, limit, offset))
    except CaseNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found.")
    except (KeyError, ValueError, ValidationError):
        raise HTTPException(status_code=503, detail="Case context unavailable.")


def build_case_response(
    case,
    alert,
    transaction_ref,
) -> CaseResponse:
    return CaseResponse(
        id=case.id,

        case_ref=(
            case.case_ref
        ),

        alert_id=(
            case.alert_id
        ),

        transaction_id=(
            alert.transaction_id
        ),

        transaction_ref=(
            transaction_ref
        ),

        alert_severity=(
            alert.severity
        ),

        status=case.status,

        priority=(
            case.priority
        ),

        assigned_to=(
            case.assigned_to
        ),

        notes=case.notes,

        created_at=(
            case.created_at
        ),

        updated_at=(
            case.updated_at
        ),
    )


@router.get(
    "",
    response_model=CasePage,
)
def read_cases(
    filters: Annotated[
        CaseFilters,
        Query(),
    ],

    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "cases.read"
        )
    ),
):
    total, rows = list_cases(
        db,
        filters,
    )

    items = [
        build_case_response(
            case,
            alert,
            transaction_ref,
        )
        for (
            case,
            alert,
            transaction_ref,
        ) in rows
    ]

    return CasePage(
        total=total,
        limit=filters.limit,
        offset=filters.offset,
        items=items,
    )


@router.get(
    "/{case_id}",
    response_model=CaseResponse,
)
def read_case(
    case_id: uuid.UUID,

    db: Session = Depends(
        get_db
    ),

    _user: StaffUser = Depends(
        require_permission(
            "cases.read"
        )
    ),
):
    try:
        (
            case,
            alert,
            transaction_ref,
        ) = get_case(
            db,
            case_id,
        )

    except CaseNotFoundError:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Case not found.",
        )

    return build_case_response(
        case,
        alert,
        transaction_ref,
    )


@router.post(
    "",
    response_model=CaseResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def create_investigation_case(
    payload: CaseCreateRequest,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    user: StaffUser = Depends(
        require_permission(
            "cases.manage"
        )
    ),
):
    try:
        (
            case,
            alert,
            transaction_ref,
            previous_alert_status,
        ) = create_case(
            db,

            alert_id=(
                payload.alert_id
            ),

            actor_ref=(
                user.email
            ),

            priority=(
                payload.priority
            ),

            assigned_to=(
                payload.assigned_to
            ),

            note=payload.note,
        )

    except (
        CaseAlertNotFoundError
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Alert not found.",
        )

    except (
        CaseAlreadyExistsError
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "Investigation case "
                "already exists for "
                "this alert."
            ),
        )

    except InvalidCaseAlertError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        )

    except (
        InvalidCaseAssigneeError
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        )

    client_ip = (
        request.client.host
        if request.client
        else None
    )

    write_audit_log(
        db,

        actor_ref=user.email,

        action="CASE_CREATED",

        resource_type=(
            "investigation_case"
        ),

        resource_id=str(
            case.id
        ),

        ip_address=client_ip,

        details={
            "case_ref":
                case.case_ref,

            "alert_id":
                str(alert.id),

            "transaction_ref":
                transaction_ref,

            "priority":
                case.priority,

            "assigned_to":
                case.assigned_to,
        },
    )

    if (
        previous_alert_status
        != alert.status
    ):
        write_audit_log(
            db,

            actor_ref=user.email,

            action=(
                "ALERT_STATUS_UPDATED"
            ),

            resource_type="alert",

            resource_id=str(
                alert.id
            ),

            ip_address=client_ip,

            details={
                "previous_status":
                    previous_alert_status,

                "new_status":
                    alert.status,

                "reason":
                    "case_created",

                "case_ref":
                    case.case_ref,

                "transaction_ref":
                    transaction_ref,
            },
        )

    db.commit()

    db.refresh(case)
    db.refresh(alert)

    return build_case_response(
        case,
        alert,
        transaction_ref,
    )


@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
)
def update_investigation_case(
    case_id: uuid.UUID,

    payload: CaseUpdateRequest,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    user: StaffUser = Depends(
        require_permission(
            "cases.manage"
        )
    ),
):
    if (
        payload.status is None
        and payload.priority is None
        and payload.assigned_to is None
        and payload.note is None
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "No case changes "
                "were requested."
            ),
        )

    if payload.status == "closed":
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "Cases must be finalized "
                "through the reviewer "
                "fraud decision workflow."
            ),
        )

    if payload.status is not None and not (payload.note and payload.note.strip()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="An investigation note is required for a case status change.",
        )

    try:
        result = update_case(
            db,

            case_id=case_id,

            actor_ref=user.email,

            expected_status=payload.expected_status,

            expected_updated_at=payload.expected_updated_at,

            new_status=(
                payload.status
            ),

            priority=(
                payload.priority
            ),

            assigned_to=(
                payload.assigned_to
            ),

            note=payload.note,
        )

    except CaseNotFoundError:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="Case not found.",
        )

    except (
        InvalidCaseTransitionError,
        StaleCaseStatusError,
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        )

    except (
        InvalidCaseAssigneeError
    ) as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=str(exc),
        )

    case = result["case"]
    alert = result["alert"]

    client_ip = (
        request.client.host
        if request.client
        else None
    )

    write_audit_log(
        db,

        actor_ref=user.email,

        action="CASE_UPDATED",

        resource_type=(
            "investigation_case"
        ),

        resource_id=str(
            case.id
        ),

        ip_address=client_ip,

        details={
            "case_ref":
                case.case_ref,

            "previous_status":
                result[
                    "previous_status"
                ],

            "new_status":
                case.status,

            "previous_priority":
                result[
                    "previous_priority"
                ],

            "new_priority":
                case.priority,

            "previous_assignee":
                result[
                    "previous_assignee"
                ],

            "new_assignee":
                case.assigned_to,

            "note_added":
                bool(
                    payload.note
                    and
                    payload.note.strip()
                ),
        },
    )

    if (
        result[
            "alert_previous_status"
        ]
        != alert.status
    ):
        write_audit_log(
            db,

            actor_ref=user.email,

            action=(
                "ALERT_STATUS_UPDATED"
            ),

            resource_type="alert",

            resource_id=str(
                alert.id
            ),

            ip_address=client_ip,

            details={
                "previous_status":
                    result[
                        "alert_previous_status"
                    ],

                "new_status":
                    alert.status,

                "reason":
                    "case_closed",

                "case_ref":
                    case.case_ref,
            },
        )

    db.commit()

    db.refresh(case)
    db.refresh(alert)

    return build_case_response(
        case,
        alert,
        result[
            "transaction_ref"
        ],
    )
