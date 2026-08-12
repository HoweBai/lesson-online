"""Tests for profile API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


class TestProfileEndpoints:
    """Test profile API endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            try:
                result = auth.register(db, "profuser", "prof@test.com", "testpass123")
                token = result["token"]
            except ValueError:
                from src.models.user import User
                user = db.query(User).filter(User.email == "prof@test.com").first()
                token = auth.create_access_token(data={"sub": str(user.id)})
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_get_profile(self, auth_client):
        """Test getting user profile."""
        response = auth_client.get("/api/v1/users/profile")
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "profile" in data

    def test_update_profile(self, auth_client):
        """Test updating user profile."""
        response = auth_client.put(
            "/api/v1/users/profile",
            json={
                "programming_level": 3,
                "learning_goal": "job_search",
                "available_hours_per_day": 3.5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "profile" in data
        assert data["profile"]["programming_level"] == 3
        assert data["profile"]["learning_goal"] == "job_search"

    def test_get_learning_progress(self, auth_client):
        """Test getting learning progress."""
        response = auth_client.get("/api/v1/users/profile/progress")
        assert response.status_code == 200
        data = response.json()
        assert "total_tutorials" in data
        assert "completed_chapters" in data

    def test_get_learning_stats(self, auth_client):
        """Test getting learning stats."""
        response = auth_client.get("/api/v1/users/profile/stats")
        assert response.status_code == 200
        data = response.json()
        assert "tutorial_stats" in data
        assert "chapter_stats" in data

    def test_profile_requires_auth(self, auth_client):
        """Test that profile endpoints require authentication."""
        auth_client.headers.clear()
        response = auth_client.get("/api/v1/users/profile")
        assert response.status_code == 401

        response = auth_client.put("/api/v1/users/profile", json={})
        assert response.status_code == 401

        response = auth_client.get("/api/v1/users/profile/progress")
        assert response.status_code == 401
