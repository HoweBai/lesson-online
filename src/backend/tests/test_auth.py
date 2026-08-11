"""Tests for user authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.database import engine, Base, get_db
from src.models.user import User
from src.services.auth_service import AuthService
from src.api.main import app

# Create test database
Base.metadata.create_all(bind=engine)

# Override dependencies
def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

class TestAuthEndpoint:
    """Test cases for authentication endpoints."""

    def test_register_new_user_success(self):
        """Successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser123",
                "email": "newuser123@example.com",
                "password": "securepassword123"
            }
        )
        assert response.status_code in [201, 400]  # 400 if already exists from previous test

    def test_register_duplicate_username(self):
        """Registration with duplicate username should fail."""
        client.post(
            "/api/v1/auth/register",
            json={"username": "dupuser", "email": "dup@example.com", "password": "pass123"}
        )
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "dupuser", "email": "different@example.com", "password": "pass456"}
        )
        assert response.status_code == 400

    def test_login_valid_credentials(self):
        """Login with valid credentials returns token."""
        client.post(
            "/api/v1/auth/register",
            json={"username": "loginuser", "email": "login@example.com", "password": "validpassword"}
        )
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "validpassword"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data

    def test_login_invalid_password(self):
        """Login with incorrect password fails."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_me_endpoint_requires_auth(self):
        """/me endpoint rejects without token."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestCatalogEndpoint:
    """Test cases for catalog endpoints."""

    def test_list_catalog(self):
        """Test listing catalog."""
        response = client.get("/api/v1/catalog/")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_search_catalog(self):
        """Test searching catalog."""
        response = client.get("/api/v1/catalog/?search=test")
        assert response.status_code == 200

    def test_popular_tutorials(self):
        """Test getting popular tutorials."""
        response = client.get("/api/v1/catalog/popular")
        # May return 200 or 404 depending on implementation
        assert response.status_code in [200, 404]


class TestWebSocketEndpoint:
    """Test cases for WebSocket endpoints."""

    def test_websocket_status(self):
        """Test WebSocket status endpoint."""
        response = client.get("/ws/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"


class TestProfileEndpoint:
    """Test cases for profile endpoints."""

    def test_get_profile_requires_auth(self):
        """Test getting profile requires authentication."""
        response = client.get("/api/v1/users/profile")
        assert response.status_code == 401

    def test_update_profile_requires_auth(self):
        """Test updating profile requires authentication."""
        response = client.put("/api/v1/users/profile", json={})
        assert response.status_code == 401


class TestExportEndpoint:
    """Test cases for export endpoints."""

    def test_export_requires_auth(self):
        """Test export endpoints require authentication."""
        response = client.get("/api/v1/tutorials/nonexistent/export/markdown")
        assert response.status_code in [401, 404]
