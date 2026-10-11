ROLE_PERMISSIONS = {
    "admin": {
        "*",
    },

    "fraud_analyst": {
        "transactions.read",
        "fraud.read",
        "fraud.review",
        "alerts.read",
        "alerts.manage",
        "cases.read",
        "cases.manage",
        "decisions.read",
    },

    "security_analyst": {
        "security.monitor",
        "login_events.read",
        "alerts.read",
        "alerts.manage",
        "audit.read",
    },

    "reviewer": {
        "transactions.read",
        "fraud.read",
        "alerts.read",
        "cases.read",
        "decisions.read",
        "decisions.review",
    },
}


def has_permission(
    role: str,
    permission: str,
) -> bool:
    permissions = ROLE_PERMISSIONS.get(
        role,
        set(),
    )

    return (
        "*" in permissions
        or permission in permissions
    )


def permissions_for_role(
    role: str,
) -> list[str]:
    permissions = ROLE_PERMISSIONS.get(
        role,
        set(),
    )

    if "*" in permissions:
        return ["*"]

    return sorted(permissions)