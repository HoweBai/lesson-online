"""Tests for export API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database import engine, Base, get_db
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
client = TestClient(app)


class TestExportEndpoints:
    """Test export API endpoints."""

    @pytest.fixture
    def auth_client(self):
        """Return a TestClient with auth headers pre-configured."""
        auth = AuthService()
        with Session(bind=engine) as db:
            try:
                result = auth.register(db, "testexpuser", "exp@test.com", "testpass123")
                token = result["token"]
            except ValueError:
                from src.models.user import User
                user = db.query(User).filter(User.email == "exp@test.com").first()
                token = auth.create_access_token(data={"sub": str(user.id)})
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_export_markdown_requires_auth(self, auth_client):
        """Test that markdown export requires authentication."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/markdown")
        assert response.status_code == 401

    def test_export_json_requires_auth(self, auth_client):
        """Test that JSON export requires authentication."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/json")
        assert response.status_code == 401

    def test_export_outline_requires_auth(self, auth_client):
        """Test that outline export requires authentication."""
        auth_client.headers.clear()
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/outline")
        assert response.status_code == 401

    def test_export_markdown_not_found(self, auth_client):
        """Test markdown export on non-existent tutorial."""
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/markdown")
        assert response.status_code == 404

    def test_export_json_not_found(self, auth_client):
        """Test JSON export on non-existent tutorial."""
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/json")
        assert response.status_code == 404

    def test_export_outline_not_found(self, auth_client):
        """Test outline export on non-existent tutorial."""
        test_id = str(uuid.uuid4())
        response = auth_client.get(f"/api/v1/tutorials/{test_id}/export/outline")
        assert response.status_code == 404
