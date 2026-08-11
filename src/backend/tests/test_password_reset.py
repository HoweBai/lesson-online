"""Tests for password reset functionality."""

import pytest
import uuid
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from src.services.password_reset_service import PasswordResetService
from src.models.user import User
from src.services.auth_service import SECRET_KEY, ALGORITHM, AuthService
from src.api.main import app
from src.database import Base, engine, get_db
from sqlalchemy.orm import Session

# Module-level engine override (same pattern as test_auth.py)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestPasswordResetService:
    """Test PasswordResetService methods."""

    def test_generate_reset_token(self, db_session, test_user):
        """Test generating a password reset token."""
        service = PasswordResetService(db=db_session)
        token = service.generate_reset_token(str(test_user.id))

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 10

        payload = service.decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "password_reset"

    def test_generate_reset_token_expires_in_one_hour(self, db_session, test_user):
        """Test that the token expires in approximately 1 hour."""
        service = PasswordResetService(db=db_session)
        token = service.generate_reset_token(str(test_user.id))
        payload = service.decode_token(token)

        exp = payload.get("exp")
        assert exp is not None
        exp_time = datetime.utcfromtimestamp(exp)
        now = datetime.utcnow()
        delta = exp_time - now
        assert 3300 <= delta.total_seconds() <= 3900

    def test_reset_password_success(self, db_session, test_user):
        """Test successful password reset."""
        service = PasswordResetService(db=db_session)
        token = service.generate_reset_token(str(test_user.id))
        new_password = "NewSecurePass123!"

        result = service.reset_password(token, new_password)
        assert result is True

        refreshed_user = db_session.query(User).filter_by(id=test_user.id).first()
        assert refreshed_user is not None
        assert refreshed_user.password_hash != "hashed_password_here"

    def test_reset_password_invalid_token(self, db_session):
        """Test reset with an invalid token."""
        service = PasswordResetService(db=db_session)
        result = service.reset_password("invalid-token-string", "NewPassword123!")
        assert result is False

    def test_reset_password_expired_token(self, db_session, test_user):
        """Test reset with an expired token."""
        service = PasswordResetService(db=db_session)
        expired_payload = {
            "sub": str(test_user.id),
            "type": "password_reset",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        result = service.reset_password(expired_token, "NewPassword123!")
        assert result is False

    def test_reset_password_wrong_token_type(self, db_session, test_user):
        """Test reset with a token that is not a password reset token."""
        service = PasswordResetService(db=db_session)
        auth_service = AuthService()
        wrong_token = auth_service.create_access_token({"sub": str(test_user.id)})
        result = service.reset_password(wrong_token, "NewPassword123!")
        assert result is False

    def test_reset_password_user_not_found(self, db_session):
        """Test reset for a non-existent user."""
        service = PasswordResetService(db=db_session)
        token = service.generate_reset_token("non-existent-user-id")
        result = service.reset_password(token, "NewPassword123!")
        assert result is False


class TestPasswordResetAPI:
    """Test password reset API endpoints."""

    def test_forgot_password_success(self):
        """Test forgot password endpoint returns token."""
        from src.database import SessionLocal
        session = SessionLocal()
        # Use unique email to avoid constraint conflicts
        unique_id = str(uuid.uuid4())
        user = User(
            id=unique_id,
            username=f"forgotuser_{unique_id}",
            email=f"forgot_{unique_id}@example.com",
            password_hash="hashed"
        )
        session.add(user)
        session.commit()
        session.close()

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": f"forgot_{unique_id}@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset_token" in data
        assert data["message"] == "Password reset token generated"

    def test_forgot_password_user_not_found(self):
        """Test forgot password with non-existent email."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset_token" in data

    def test_reset_password_success(self):
        """Test reset password endpoint."""
        from src.database import SessionLocal
        from src.services.password_reset_service import PasswordResetService

        session = SessionLocal()
        unique_id = str(uuid.uuid4())
        user = User(
            id=unique_id,
            username=f"resetuser_{unique_id}",
            email=f"reset_{unique_id}@example.com",
            password_hash="old_hashed_password"
        )
        session.add(user)
        session.commit()

        service = PasswordResetService(db=session)
        token = service.generate_reset_token(unique_id)

        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": token,
                "new_password": "NewSecurePass123!"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password reset successful"

        # Verify old password no longer works
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"reset_{unique_id}@example.com",
                "password": "old_hashed_password"
            }
        )
        assert login_response.status_code == 401

        # Verify new password works
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": f"reset_{unique_id}@example.com",
                "password": "NewSecurePass123!"
            }
        )
        assert login_response.status_code == 200
        session.close()

    def test_reset_password_invalid_token(self):
        """Test reset password with invalid token."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token",
                "new_password": "NewPassword123!"
            }
        )
        assert response.status_code == 400

    def test_reset_password_missing_fields(self):
        """Test reset password with missing fields."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "some-token"}
        )
        assert response.status_code == 422

    def test_forgot_password_missing_email(self):
        """Test forgot password with missing email."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={}
        )
        assert response.status_code == 422
