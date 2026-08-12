"""Extended tests for auth endpoints."""

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


class TestAuthExtended:
    """Extended authentication tests."""

    def test_register_duplicate_email(self):
        """Test registration with duplicate email."""
        c = TestClient(app)
        payload = {
            "username": "dupuser99",
            "email": "dup99@test.com",
            "password": "testpass123"
        }
        response1 = c.post("/api/v1/auth/register", json=payload)
        assert response1.status_code in [201, 400]

        payload2 = {
            "username": "dupuser99b",
            "email": "dup99@test.com",
            "password": "testpass123"
        }
        response2 = c.post("/api/v1/auth/register", json=payload2)
        assert response2.status_code == 400

    def test_register_duplicate_username(self):
        """Test registration with duplicate username."""
        c = TestClient(app)
        payload = {
            "username": "sameuser99",
            "email": "same99a@test.com",
            "password": "testpass123"
        }
        c.post("/api/v1/auth/register", json=payload)

        payload2 = {
            "username": "sameuser99",
            "email": "same99b@test.com",
            "password": "testpass123"
        }
        response = c.post("/api/v1/auth/register", json=payload2)
        assert response.status_code == 400

    def test_login_wrong_password(self):
        """Test login with wrong password."""
        auth = AuthService()
        with Session(bind=engine) as db:
            auth.register(db, "wrongpwduser", "wrongpwd@test.com", "correctpass123")

        c = TestClient(app)
        response = c.post("/api/v1/auth/login", json={
            "email": "wrongpwd@test.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401

    def test_me_endpoint(self):
        """Test getting current user info."""
        auth = AuthService()
        with Session(bind=engine) as db:
            try:
                result = auth.register(db, "meuser2", "me2@test.com", "testpass123")
            except ValueError:
                from src.models.user import User
                user = db.query(User).filter(User.email == "me2@test.com").first()
                result = {"token": auth.create_access_token(data={"sub": str(user.id)})}
            token = result["token"]

        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        response = c.get("/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "username" in data
        assert "email" in data

    def test_logout_endpoint(self):
        """Test logout endpoint."""
        c = TestClient(app)
        response = c.post("/api/v1/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
