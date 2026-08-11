"""Tests for bookmark API endpoints."""
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import text
from src.database import engine, Base, get_db
from src.services.auth_service import get_current_user
from sqlalchemy.orm import Session
import pytest

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


def override_get_current_user():
    from src.models.user import User
    return User(id="test-user-1", username="testuser", email="test@test.com")


@pytest.fixture
def bookmark_client():
    from src.api.main import app
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _clean_db():
    db = Session(bind=engine)
    db.execute(text("DELETE FROM user_bookmarks"))
    db.execute(text("DELETE FROM chapters"))
    db.execute(text("DELETE FROM tutorials"))
    db.commit()
    db.close()


def _insert_tutorial(db, tutorial_id, owner_id="test-user-1"):
    db.execute(text(
        "INSERT INTO tutorials (id, owner_id, title, description, status, is_public, total_chapters, current_chapter, created_at, updated_at) VALUES (:id, :owner_id, :title, :description, :status, :is_public, :total_chapters, :current_chapter, :created_at, :updated_at)"
    ), {
        "id": tutorial_id,
        "owner_id": owner_id,
        "title": "Test Tutorial",
        "description": "A test tutorial",
        "status": "published",
        "is_public": True,
        "total_chapters": 3,
        "current_chapter": 1,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    db.commit()


def test_bookmark_tutorial(bookmark_client):
    _clean_db()
    tutorial_id = "test-bm-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)

    resp = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    db = Session(bind=engine)
    count = db.execute(text("SELECT COUNT(*) FROM user_bookmarks WHERE user_id=:uid AND tutorial_id=:tid"),
                       {"uid": "test-user-1", "tid": tutorial_id}).fetchone()[0]
    db.close()
    assert count == 1


def test_duplicate_bookmark(bookmark_client):
    _clean_db()
    tutorial_id = "test-dup-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)

    resp1 = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")
    resp2 = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp2.json()["message"] == "Already bookmarked"


def test_unbookmark_tutorial(bookmark_client):
    _clean_db()
    tutorial_id = "test-ub-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)

    bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")
    resp = bookmark_client.delete(f"/api/v1/bookmarks/{tutorial_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    db = Session(bind=engine)
    count = db.execute(text("SELECT COUNT(*) FROM user_bookmarks WHERE user_id=:uid AND tutorial_id=:tid"),
                       {"uid": "test-user-1", "tid": tutorial_id}).fetchone()[0]
    db.close()
    assert count == 0


def test_bookmark_not_found(bookmark_client):
    resp = bookmark_client.post("/api/v1/bookmarks/nonexistent")
    assert resp.status_code == 404


def test_list_bookmarks(bookmark_client):
    _clean_db()
    tutorial_id = "test-lb-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)
    bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")

    resp = bookmark_client.get("/api/v1/bookmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data
    assert len(data["data"]) >= 1


def test_list_bookmarks_empty(bookmark_client):
    resp = bookmark_client.get("/api/v1/bookmarks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"] == []
    assert data["pagination"]["total"] == 0
