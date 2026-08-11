"""Tests for Comment API endpoints."""
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
def comment_client():
    from src.api.main import app
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _clean_db():
    db = Session(bind=engine)
    db.execute(text("DELETE FROM tutorial_comments"))
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


def test_create_comment(comment_client):
    from src.models.comment import Comment
    _clean_db()
    tutorial_id = "test-cmt-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)

    resp = comment_client.post(
        f"/api/v1/tutorials/{tutorial_id}/comments",
        json={"content": "Great tutorial!"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Great tutorial!"
    assert data["user_id"] == "test-user-1"

    db = Session(bind=engine)
    comment = db.query(Comment).filter_by(tutorial_id=tutorial_id).first()
    db.close()
    assert comment is not None


def test_get_comments(comment_client):
    from src.models.comment import Comment
    _clean_db()
    tutorial_id = "test-gc-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)

    db = Session(bind=engine)
    Comment.create(db=db, user_id="test-user-1", tutorial_id=tutorial_id, content="Hello")
    db.close()

    resp = comment_client.get(f"/api/v1/tutorials/{tutorial_id}/comments")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) >= 1


def test_like_comment(comment_client):
    from src.models.comment import Comment
    _clean_db()
    tutorial_id = "test-like-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)

    db = Session(bind=engine)
    comment = Comment.create(db=db, user_id="test-user-1", tutorial_id=tutorial_id, content="Like me")
    comment_id = comment.id
    db.close()

    resp = comment_client.post(f"/api/v1/comments/{comment_id}/like")
    assert resp.status_code == 200
    assert resp.json()["like_count"] == 1


def test_delete_own_comment(comment_client):
    from src.models.comment import Comment
    _clean_db()
    tutorial_id = "test-del-tutorial"
    _insert_tutorial(Session(bind=engine), tutorial_id)

    db = Session(bind=engine)
    comment = Comment.create(db=db, user_id="test-user-1", tutorial_id=tutorial_id, content="Delete me")
    comment_id = comment.id
    db.close()

    resp = comment_client.delete(f"/api/v1/comments/{comment_id}")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
