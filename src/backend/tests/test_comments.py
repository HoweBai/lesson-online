"""Tests for comment API endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session
from src.services.auth_service import AuthService
import uuid

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


class TestCommentEndpoints:
    """Test comment API endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            try:
                result = auth.register(db, "testcomuser", "com@test.com", "testpass123")
                token = result["token"]
            except ValueError:
                # User already exists from a previous test run; get token from existing user
                from src.models.user import User
                user = db.query(User).filter(User.email == "com@test.com").first()
                token = auth.create_access_token(data={"sub": str(user.id)})
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_create_comment_requires_auth(self, auth_client):
        """Test that creating comments requires authentication."""
        auth_client.headers.clear()
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.post(
            f"/api/v1/tutorials/{test_tutorial_id}/comments",
            json={"content": "Test comment"}
        )
        assert response.status_code == 401

    def test_get_comments_requires_auth(self, auth_client):
        """Test that getting comments requires authentication."""
        auth_client.headers.clear()
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/comments")
        assert response.status_code == 401

    def test_create_comment_on_nonexistent_tutorial(self, auth_client):
        """Test creating a comment on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.post(
            f"/api/v1/tutorials/{test_tutorial_id}/comments",
            json={"content": "Test comment"}
        )
        assert response.status_code == 404

    def test_get_comments_on_nonexistent_tutorial(self, auth_client):
        """Test getting comments on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/comments")
        assert response.status_code == 404
