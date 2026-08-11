"""Tests for the AuditLog model."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base, get_db
from src.models.audit_log import AuditLog


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_audit_log(db_session):
    log = AuditLog.create(
        db=db_session,
        user_id="user-123",
        action_type="content_scanned",
        details={"score": 0.5},
        ip_address="127.0.0.1"
    )
    assert log.id is not None
    assert log.action_type == "content_scanned"
    assert log.user_id == "user-123"
    assert log.ip_address == "127.0.0.1"
    assert log.details_json == {"score": 0.5}


def test_audit_log_to_dict(db_session):
    log = AuditLog.create(
        db=db_session,
        user_id="user-456",
        action_type="login",
        details={"success": True}
    )
    d = log.to_dict()
    assert "id" in d
    assert d["action_type"] == "login"
    assert d["user_id"] == "user-456"
    assert d["details"] == {"success": True}


def test_audit_log_default_timestamps(db_session):
    log = AuditLog.create(
        db=db_session,
        user_id="user-789",
        action_type="logout",
    )
    assert log.success is not None
    assert log.timestamp is not None


def test_audit_log_optional_fields(db_session):
    log = AuditLog.create(
        db=db_session,
        user_id=None,
        action_type="system_event",
    )
    assert log.user_id is None
    assert log.ip_address is None
    assert log.details_json is None
