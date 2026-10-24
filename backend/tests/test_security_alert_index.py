
from sqlalchemy import MetaData
from sqlalchemy.schema import CreateIndex
from sqlalchemy.dialects import postgresql

from app.models.alert import Alert


def test_unique_index_is_defined():
    indexes = {
        index.name: index
        for index in Alert.__table__.indexes
    }

    index = indexes["uq_alerts_failed_login_event"]

    assert index.unique is True
    assert [col.name for col in index.columns] == [
        "alert_type",
        "login_event_id",
    ]


def test_unique_index_is_partial():
    index = next(
        item for item in Alert.__table__.indexes
        if item.name == "uq_alerts_failed_login_event"
    )

    sql = str(
        CreateIndex(index).compile(
            dialect=postgresql.dialect()
        )
    )

    assert "CREATE UNIQUE INDEX" in sql
    assert "FAILED_LOGIN_BURST" in sql
    assert "login_event_id IS NOT NULL" in sql


def test_alert_metadata_uses_existing_table():
    assert Alert.__table__.name == "alerts"
    assert "login_event_id" in Alert.__table__.columns
    assert "alert_type" in Alert.__table__.columns
