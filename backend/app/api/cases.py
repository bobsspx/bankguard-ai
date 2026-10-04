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
from sqlalchemy.orm import Session

from app.api.dependencies import (
    require_permission,
)
from app.db.session import get_db
from app.models.staff_user import (
    StaffUser,
)
from app.schemas.case import (
    CaseCreateRequest,
    CaseFilters,
    CasePage,
    CaseResponse,
    CaseUpdateRequest,
)
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
    create_case,
    get_case,
    list_cases,
    update_case,
)


router = APIRouter(
    prefix="/api/v1/cases",
    tags=["cases"],
)


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

    try:
        result = update_case(
            db,

            case_id=case_id,

            actor_ref=user.email,

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
        InvalidCaseTransitionError
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