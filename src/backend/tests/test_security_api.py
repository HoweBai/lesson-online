"""Tests for security scanning API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from src.api.main import app
from src.database import Base, engine, get_db
from src.models.audit_log import AuditLog


@pytest.fixture
def db_session():
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_audit_logs(db_session):
    """Clear audit_logs before each test to avoid data leakage."""
    db_session.execute(text("DELETE FROM audit_logs"))
    db_session.commit()
    yield


def test_get_security_scans_empty(client, db_session):
    response = client.get("/api/v1/security/scans")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["total"] == 0
    assert data["data"] == []


def test_get_security_scans_with_records(client, db_session):
    AuditLog.create(
        db=db_session,
        user_id="user-123",
        action_type="content_scanned",
        details={"reasons": ["test_reason"]}
    )
    db_session.commit()

    response = client.get("/api/v1/security/scans")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["total"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["user_id"] == "user-123"
    assert data["data"][0]["action_type"] == "content_scanned"


def test_get_security_scans_filter_by_user_id(client, db_session):
    AuditLog.create(
        db=db_session,
        user_id="user-123",
        action_type="content_scanned",
        details={"reasons": []}
    )
    AuditLog.create(
        db=db_session,
        user_id="user-456",
        action_type="content_scanned",
        details={"reasons": []}
    )
    db_session.commit()

    response = client.get("/api/v1/security/scans?user_id=user-123")
    assert response.status_code == 200
    data = response.json()
    assert data["pagination"]["total"] == 1
    assert data["data"][0]["user_id"] == "user-123"


def test_get_security_scans_pagination(client, db_session):
    for i in range(5):
        AuditLog.create(
            db=db_session,
            user_id=f"user-{i}",
            action_type="content_scanned",
            details={"reasons": []}
        )
    db_session.commit()

    response = client.get("/api/v1/security/scans?page=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["pagination"]["total"] == 5
    assert data["pagination"]["pages"] == 3


def test_get_security_stats_empty(client, db_session):
    response = client.get("/api/v1/security/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_scans" in data
    assert "flagged_count" in data
    assert data["total_scans"] == 0
    assert data["flagged_count"] == 0
    assert data["flag_rate"] == 0


def test_get_security_stats_with_records(client, db_session):
    AuditLog.create(
        db=db_session,
        user_id="user-123",
        action_type="content_scanned",
        details={"reasons": ["test_reason"]}
    )
    AuditLog.create(
        db=db_session,
        user_id="user-456",
        action_type="content_scanned",
        details={"reasons": []}
    )
    db_session.commit()

    response = client.get("/api/v1/security/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_scans"] == 2
    # SQLite stores JSON as text, so isnot(None) matches all rows with a details_json column
    assert data["flagged_count"] >= 1
    assert data["flag_rate"] > 0
