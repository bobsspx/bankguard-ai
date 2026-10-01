from app.core.rbac import has_permission


def test_admin_has_all_permissions():
    assert has_permission(
        "admin",
        "staff.manage",
    )


def test_fraud_analyst_can_review_fraud():
    assert has_permission(
        "fraud_analyst",
        "fraud.review",
    )


def test_fraud_analyst_cannot_manage_staff():
    assert not has_permission(
        "fraud_analyst",
        "staff.manage",
    )


def test_security_analyst_can_monitor_security():
    assert has_permission(
        "security_analyst",
        "security.monitor",
    )


def test_reviewer_is_read_only():
    assert has_permission(
        "reviewer",
        "cases.read",
    )

    assert not has_permission(
        "reviewer",
        "cases.manage",
    )