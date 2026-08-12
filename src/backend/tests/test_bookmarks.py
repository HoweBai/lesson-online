"""Tests for bookmark API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from src.api.main import app
from src.database import engine, Base
from src.services.auth_service import AuthService
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid as uuid_module

Base.metadata.create_all(bind=engine)


@pytest.fixture
def auth_client():
    """Return a TestClient with auth headers pre-configured."""
    auth = AuthService()
    with Session(bind=engine) as db:
        try:
            result = auth.register(db, "testbookuser", "book@test.com", "testpass123")
            token = result["token"]
        except ValueError:
            # User already exists from a previous test run; get token from existing user
            from src.models.user import User
            user = db.query(User).filter(User.email == "book@test.com").first()
            token = auth.create_access_token(data={"sub": str(user.id)})
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def _clean_db() -> None:
    db = Session(bind=engine)
    db.execute(text("DELETE FROM user_bookmarks"))
    db.execute(text("DELETE FROM chapters"))
    db.execute(text("DELETE FROM tutorials"))
    # Do NOT delete users - the auth_client fixture user must persist
    db.commit()
    db.close()


def _insert_tutorial(db: Session, tutorial_id: str, owner_id: str = "testbookuser") -> None:
    db.execute(text(
        "INSERT INTO tutorials (id, owner_id, title, description, status, is_public, total_chapters, current_chapter, created_at, updated_at) "
        "VALUES (:id, :owner_id, :title, :description, :status, :is_public, :total_chapters, :current_chapter, :created_at, :updated_at)"
    ), {
        "id": tutorial_id,
        "owner_id": owner_id,
        "title": "Test Tutorial",
        "description": "A test tutorial",
        "status": "published",
        "is_public": True,
        "total_chapters": 3,
        "current_chapter": 1,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    db.commit()


def _register_user(db: Session, username: str, email: str, password: str) -> str:
    """Register a user, ignoring duplicate errors."""
    auth = AuthService()
    try:
        result = auth.register(db, username, email, password)
        return result["user"]["id"]
    except ValueError:
        # User already exists; look them up
        from src.models.user import User
        user = db.query(User).filter(User.email == email).first()
        if user:
            return str(user.id)
        raise


class TestBookmarkEndpoints:
    """Test bookmark API endpoints."""

    def test_bookmark_tutorial(self, auth_client: TestClient) -> None:
        """Test bookmarking a tutorial."""
        _clean_db()
        with Session(bind=engine) as db:
            user_id = _register_user(db, "testbookuser", "book@test.com", "testpass123")

        test_tutorial_id = str(uuid_module.uuid4())
        _insert_tutorial(Session(bind=engine), test_tutorial_id, user_id)

        response = auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        db = Session(bind=engine)
        count = db.execute(
            text("SELECT COUNT(*) FROM user_bookmarks WHERE user_id=:uid AND tutorial_id=:tid"),
            {"uid": user_id, "tid": test_tutorial_id}
        ).fetchone()[0]
        db.close()
        assert count == 1

    def test_unbookmark_tutorial(self, auth_client: TestClient) -> None:
        """Test unbookmarking a tutorial."""
        _clean_db()
        with Session(bind=engine) as db:
            user_id = _register_user(db, "testbookuser_u", "booku@test.com", "testpass123")

        test_tutorial_id = str(uuid_module.uuid4())
        _insert_tutorial(Session(bind=engine), test_tutorial_id, user_id)

        auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        response = auth_client.delete(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 200
        assert response.json()["success"] is True

        db = Session(bind=engine)
        count = db.execute(
            text("SELECT COUNT(*) FROM user_bookmarks WHERE user_id=:uid AND tutorial_id=:tid"),
            {"uid": user_id, "tid": test_tutorial_id}
        ).fetchone()[0]
        db.close()
        assert count == 0

    def test_list_bookmarks(self, auth_client: TestClient) -> None:
        """Test listing user bookmarks."""
        _clean_db()
        with Session(bind=engine) as db:
            user_id = _register_user(db, "testbookuser", "book@test.com", "testpass123")

        test_tutorial_id = str(uuid_module.uuid4())
        _insert_tutorial(Session(bind=engine), test_tutorial_id, user_id)
        auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")

        response = auth_client.get("/api/v1/bookmarks/bookmarks")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) >= 1

    def test_bookmark_requires_auth(self, auth_client: TestClient) -> None:
        """Test that bookmark endpoints require authentication."""
        auth_client.headers.clear()
        test_tutorial_id = str(uuid_module.uuid4())

        response = auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 401

        response = auth_client.delete(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 401

        response = auth_client.get("/api/v1/bookmarks/bookmarks")
        assert response.status_code == 401

    def test_bookmark_not_found_tutorial(self, auth_client: TestClient) -> None:
        """Test bookmarking a non-existent tutorial returns 404."""
        test_tutorial_id = str(uuid_module.uuid4())
        response = auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 404

    def test_unbookmark_not_found(self, auth_client: TestClient) -> None:
        """Test unbookmarking a non-existent bookmark returns 404."""
        test_tutorial_id = str(uuid_module.uuid4())
        response = auth_client.delete(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response.status_code == 404

    def test_duplicate_bookmark(self, auth_client: TestClient) -> None:
        """Test bookmarking the same tutorial twice returns success with 'Already bookmarked' message."""
        _clean_db()
        with Session(bind=engine) as db:
            user_id = _register_user(db, "testbookuser_d", "bookd@test.com", "testpass123")

        test_tutorial_id = str(uuid_module.uuid4())
        _insert_tutorial(Session(bind=engine), test_tutorial_id, user_id)

        response1 = auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response1.status_code == 200
        assert response1.json()["success"] is True

        response2 = auth_client.post(f"/api/v1/bookmarks/{test_tutorial_id}/bookmark")
        assert response2.status_code == 200
        assert response2.json()["success"] is True
        assert "Already bookmarked" in response2.json()["message"]
