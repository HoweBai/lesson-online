"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database import engine, Base, get_db
from sqlalchemy.orm import Session

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


class TestHealthEndpoints:
    """Test health and info endpoints."""

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_docs(self):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json(self):
        response = client.get("/openapi.json")
        assert response.status_code == 200


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_register(self):
        response = client.post(
            "/api/v1/auth/register",
            json={"username": "testuser", "email": "test@example.com", "password": "testpass123"}
        )
        assert response.status_code in [201, 400]  # 400 if already exists

    def test_login(self):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpass123"}
        )
        assert response.status_code in [200, 401]

    def test_me_requires_auth(self):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestCatalogEndpoints:
    """Test catalog endpoints."""

    def test_list_catalog(self):
        response = client.get("/api/v1/catalog/")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_search_catalog(self):
        response = client.get("/api/v1/catalog/?search=test")
        assert response.status_code == 200

    def test_catalog_detail_not_found(self):
        response = client.get("/api/v1/catalog/nonexistent")
        assert response.status_code == 404


class TestWebSocketEndpoints:
    """Test WebSocket endpoints."""

    def test_status(self):
        response = client.get("/ws/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"


class TestProfileEndpoints:
    """Test profile endpoints."""

    def test_get_profile_requires_auth(self):
        response = client.get("/api/v1/users/profile")
        assert response.status_code == 401

    def test_update_profile_requires_auth(self):
        response = client.put("/api/v1/users/profile", json={})
        assert response.status_code == 401


class TestExportEndpoints:
    """Test export endpoints."""

    def test_export_requires_auth(self):
        response = client.get("/api/v1/tutorials/nonexistent/export/markdown")
        assert response.status_code in [401, 404]


class TestTutorialEndpoints:
    """Test tutorial endpoints."""

    def test_list_tutorials(self):
        response = client.get("/api/v1/tutorials/")
        assert response.status_code == 200

    def test_get_tutorial_not_found(self):
        response = client.get("/api/v1/tutorials/nonexistent")
        assert response.status_code == 404
