import uuid
from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    func,
    select,
    text,
)
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.investigation_case import (
    InvestigationCase,
)
from app.models.staff_user import StaffUser
from app.models.transaction import Transaction
from app.schemas.case import CaseFilters


class CaseNotFoundError(
    Exception
):
    pass


class CaseAlertNotFoundError(
    Exception
):
    pass


class CaseAlreadyExistsError(
    Exception
):
    pass


class InvalidCaseTransitionError(
    Exception
):
    pass


class InvalidCaseAssigneeError(
    Exception
):
    pass


class InvalidCaseAlertError(
    Exception
):
    pass


CASE_ALLOWED_TRANSITIONS = {
    "open": {
        "investigating",
        "closed",
    },

    "investigating": {
        "pending_review",
        "closed",
    },

    "pending_review": {
        "investigating",
        "closed",
    },

    "closed": set(),
}


def priority_from_severity(
    severity: str,
) -> str:
    mapping = {
        "low": "low",
        "medium": "medium",
        "high": "high",
        "critical": "critical",
    }

    return mapping.get(
        severity,
        "medium",
    )


def apply_case_transition(
    case: InvestigationCase,
    new_status: str,
) -> tuple[str, str]:
    previous_status = (
        case.status
    )

    if (
        previous_status
        == new_status
    ):
        return (
            previous_status,
            new_status,
        )

    allowed = (
        CASE_ALLOWED_TRANSITIONS
        .get(
            previous_status
        )
    )

    if allowed is None:
        raise (
            InvalidCaseTransitionError(
                (
                    "Unknown current "
                    "case status: "
                    f"{previous_status}"
                )
            )
        )

    if new_status not in allowed:
        raise (
            InvalidCaseTransitionError(
                (
                    "Invalid case "
                    "transition: "
                    f"{previous_status}"
                    " -> "
                    f"{new_status}"
                )
            )
        )

    case.status = new_status

    return (
        previous_status,
        new_status,
    )


def append_case_note(
    case: InvestigationCase,
    *,
    actor_ref: str,
    note: str,
) -> None:
    clean_note = (
        note.strip()
    )

    if not clean_note:
        return

    timestamp = (
        datetime.now(
            timezone.utc
        )
        .isoformat(
            timespec="seconds"
        )
    )

    entry = (
        f"[{timestamp}] "
        f"{actor_ref}: "
        f"{clean_note}"
    )

    if case.notes:
        case.notes = (
            f"{case.notes}\n"
            f"{entry}"
        )
    else:
        case.notes = entry


def validate_assignee(
    db: Session,
    email: str | None,
) -> str | None:
    if email is None:
        return None

    clean_email = (
        email
        .strip()
        .lower()
    )

    if not clean_email:
        return None

    user = db.scalar(
        select(
            StaffUser
        ).where(
            StaffUser.email
            == clean_email
        )
    )

    if (
        user is None
        or not user.is_active
        or user.role
        not in {
            "fraud_analyst",
            "admin",
        }
    ):
        raise (
            InvalidCaseAssigneeError(
                (
                    "Case assignee must "
                    "be an active fraud "
                    "analyst or admin."
                )
            )
        )

    return user.email


def generate_case_ref(
    db: Session,
) -> str:
    # PostgreSQL transaction-level
    # advisory lock prevents two
    # concurrent case creations from
    # receiving the same sequence.
    db.execute(
        text(
            "SELECT "
            "pg_advisory_xact_lock"
            "(845201)"
        )
    )

    year = (
        datetime.now(
            timezone.utc
        ).year
    )

    prefix = (
        f"CASE-{year}-"
    )

    latest = db.scalar(
        select(
            InvestigationCase.case_ref
        )
        .where(
            InvestigationCase
            .case_ref
            .like(
                f"{prefix}%"
            )
        )
        .order_by(
            InvestigationCase
            .case_ref
            .desc()
        )
        .limit(1)
    )

    next_number = 1

    if latest:
        try:
            next_number = (
                int(
                    latest.rsplit(
                        "-",
                        1,
                    )[1]
                )
                + 1
            )
        except (
            ValueError,
            IndexError,
        ):
            next_number = 1

    return (
        f"{prefix}"
        f"{next_number:06d}"
    )


def create_case(
    db: Session,
    *,
    alert_id: uuid.UUID,
    actor_ref: str,
    priority: str | None,
    assigned_to: str | None,
    note: str | None,
):
    alert = db.scalar(
        select(Alert)
        .where(
            Alert.id
            == alert_id
        )
        .with_for_update()
    )

    if alert is None:
        raise (
            CaseAlertNotFoundError
        )

    if alert.status in {
        "resolved",
        "dismissed",
    }:
        raise (
            InvalidCaseAlertError(
                (
                    "Cannot create a case "
                    "from a terminal alert."
                )
            )
        )

    existing = db.scalar(
        select(
            InvestigationCase
        ).where(
            InvestigationCase.alert_id
            == alert.id
        )
    )

    if existing is not None:
        raise (
            CaseAlreadyExistsError
        )

    clean_assignee = (
        validate_assignee(
            db,
            assigned_to,
        )
    )

    case = InvestigationCase(
        case_ref=(
            generate_case_ref(
                db
            )
        ),

        alert_id=alert.id,

        status="open",

        priority=(
            priority
            or priority_from_severity(
                alert.severity
            )
        ),

        assigned_to=(
            clean_assignee
        ),
    )

    if note:
        append_case_note(
            case,
            actor_ref=actor_ref,
            note=note,
        )

    previous_alert_status = (
        alert.status
    )

    if alert.status == "open":
        alert.status = (
            "investigating"
        )

        alert.resolved_at = None

    db.add(case)

    db.flush()

    transaction_ref = None

    if (
        alert.transaction_id
        is not None
    ):
        transaction_ref = (
            db.scalar(
                select(
                    Transaction
                    .transaction_ref
                )
                .where(
                    Transaction.id
                    == alert.transaction_id
                )
            )
        )

    return (
        case,
        alert,
        transaction_ref,
        previous_alert_status,
    )


def update_case(
    db: Session,
    *,
    case_id: uuid.UUID,
    actor_ref: str,
    new_status: str | None,
    priority: str | None,
    assigned_to: str | None,
    note: str | None,
):
    case = db.scalar(
        select(
            InvestigationCase
        )
        .where(
            InvestigationCase.id
            == case_id
        )
        .with_for_update()
    )

    if case is None:
        raise CaseNotFoundError

    alert = db.scalar(
        select(Alert)
        .where(
            Alert.id
            == case.alert_id
        )
        .with_for_update()
    )

    if alert is None:
        raise (
            CaseAlertNotFoundError
        )

    previous_status = (
        case.status
    )

    if new_status is not None:
        apply_case_transition(
            case,
            new_status,
        )

    previous_priority = (
        case.priority
    )

    if priority is not None:
        case.priority = priority

    previous_assignee = (
        case.assigned_to
    )

    if assigned_to is not None:
        case.assigned_to = (
            validate_assignee(
                db,
                assigned_to,
            )
        )

    if note:
        append_case_note(
            case,
            actor_ref=actor_ref,
            note=note,
        )

    alert_previous_status = (
        alert.status
    )

    if (
        case.status == "closed"
        and alert.status
        not in {
            "resolved",
            "dismissed",
        }
    ):
        alert.status = "resolved"

        alert.resolved_at = (
            datetime.now(
                timezone.utc
            )
        )

    transaction_ref = None

    if (
        alert.transaction_id
        is not None
    ):
        transaction_ref = (
            db.scalar(
                select(
                    Transaction
                    .transaction_ref
                )
                .where(
                    Transaction.id
                    == alert.transaction_id
                )
            )
        )

    db.add(case)

    return {
        "case": case,

        "alert": alert,

        "transaction_ref":
            transaction_ref,

        "previous_status":
            previous_status,

        "previous_priority":
            previous_priority,

        "previous_assignee":
            previous_assignee,

        "alert_previous_status":
            alert_previous_status,
    }


def list_cases(
    db: Session,
    filters: CaseFilters,
):
    conditions = []

    if filters.status:
        conditions.append(
            InvestigationCase.status
            == filters.status
        )

    if filters.priority:
        conditions.append(
            InvestigationCase.priority
            == filters.priority
        )

    count_statement = (
        select(
            func.count(
                InvestigationCase.id
            )
        )
    )

    statement = (
        select(
            InvestigationCase,
            Alert,
            Transaction.transaction_ref,
        )
        .join(
            Alert,
            Alert.id
            == InvestigationCase.alert_id,
        )
        .outerjoin(
            Transaction,
            Transaction.id
            == Alert.transaction_id,
        )
    )

    if conditions:
        count_statement = (
            count_statement
            .where(
                *conditions
            )
        )

        statement = (
            statement
            .where(
                *conditions
            )
        )

    total = (
        db.scalar(
            count_statement
        )
        or 0
    )

    rows = db.execute(
        statement
        .order_by(
            InvestigationCase
            .updated_at
            .desc()
        )
        .limit(
            filters.limit
        )
        .offset(
            filters.offset
        )
    ).all()

    return (
        int(total),
        rows,
    )


def get_case(
    db: Session,
    case_id: uuid.UUID,
):
    row = db.execute(
        select(
            InvestigationCase,
            Alert,
            Transaction.transaction_ref,
        )
        .join(
            Alert,
            Alert.id
            == InvestigationCase.alert_id,
        )
        .outerjoin(
            Transaction,
            Transaction.id
            == Alert.transaction_id,
        )
        .where(
            InvestigationCase.id
            == case_id
        )
    ).first()

    if row is None:
        raise CaseNotFoundError

    return row