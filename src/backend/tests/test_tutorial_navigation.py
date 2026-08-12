"""Tests for tutorial chapter navigation endpoints."""

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


class TestChapterNavigation:
    """Test chapter navigation endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            try:
                result = auth.register(db, "testnavuser", "nav@test.com", "testpass123")
                token = result["token"]
            except ValueError:
                from src.models.user import User
                user = db.query(User).filter(User.email == "nav@test.com").first()
                token = auth.create_access_token(data={"sub": str(user.id)})
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_list_chapters_on_nonexistent_tutorial(self, auth_client):
        """Test listing chapters on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/chapters")
        assert response.status_code == 404

    def test_get_chapter_content_on_nonexistent_tutorial(self, auth_client):
        """Test getting chapter content on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/chapters/1")
        assert response.status_code == 404

    def test_get_chapter_status_on_nonexistent_tutorial(self, auth_client):
        """Test getting chapter status on a non-existent tutorial."""
        test_tutorial_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_tutorial_id}/chapters/1/status")
        assert response.status_code == 404
