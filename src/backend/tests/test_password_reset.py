"""Tests for password reset functionality."""

import pytest
from datetime import datetime, timedelta
from jose import jwt
from unittest.mock import MagicMock, patch

from src.services.password_reset_service import PasswordResetService
from src.models.user import User
from src.services.auth_service import SECRET_KEY, ALGORITHM


class TestPasswordResetService:
    """Test PasswordResetService methods."""

    def test_generate_reset_token(self, db_session, test_user):
        """Test generating a password reset token."""
        service = PasswordResetService()
        token = service.generate_reset_token(str(test_user.id))

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 10

        # Decode and verify
        payload = service.decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(test_user.id)
        assert payload["type"] == "password_reset"

    def test_generate_reset_token_expires_in_one_hour(self, db_session, test_user):
        """Test that the token expires in approximately 1 hour."""
        service = PasswordResetService()
        token = service.generate_reset_token(str(test_user.id))
        payload = service.decode_token(token)

        exp = payload.get("exp")
        assert exp is not None
        exp_time = datetime.utcfromtimestamp(exp)
        now = datetime.utcnow()
        delta = exp_time - now

        # Should expire within 55-65 minutes
        assert 3300 <= delta.total_seconds() <= 3900

    def test_reset_password_success(self, db_session, test_user):
        """Test successful password reset."""
        service = PasswordResetService()
        token = service.generate_reset_token(str(test_user.id))
        new_password = "NewSecurePass123!"

        result = service.reset_password(token, new_password)

        assert result is True

        # Verify the password was actually changed
        refreshed_user = db_session.query(User).filter_by(id=test_user.id).first()
        assert refreshed_user is not None
        assert refreshed_user.password_hash != "hashed_password_here"

    def test_reset_password_invalid_token(self, db_session):
        """Test reset with an invalid token."""
        service = PasswordResetService()
        result = service.reset_password("invalid-token-string", "NewPassword123!")

        assert result is False

    def test_reset_password_expired_token(self, db_session, test_user):
        """Test reset with an expired token."""
        service = PasswordResetService()
        # Create an expired token manually
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
        service = PasswordResetService()
        # Create an access token (wrong type)
        from src.services.auth_service import AuthService
        auth_service = AuthService()
        wrong_token = auth_service.create_access_token({"sub": str(test_user.id)})

        result = service.reset_password(wrong_token, "NewPassword123!")
        assert result is False

    def test_reset_password_user_not_found(self, db_session):
        """Test reset for a non-existent user."""
        service = PasswordResetService()
        token = service.generate_reset_token("non-existent-user-id")

        result = service.reset_password(token, "NewPassword123!")
        assert result is False


class TestPasswordResetAPI:
    """Test password reset API endpoints."""

    def test_forgot_password_success(self, client, db_session):
        """Test forgot password endpoint returns token."""
        from src.models.user import User
        user = User(
            id="forgot-test-id",
            username="forgotuser",
            email="forgot@example.com",
            password_hash="hashed"
        )
        db_session.add(user)
        db_session.commit()

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "reset_token" in data
        assert data["message"] == "Password reset token generated"

    def test_forgot_password_user_not_found(self, client):
        """Test forgot password with non-existent email."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"}
        )

        assert response.status_code == 200
        # Should not reveal whether user exists
        data = response.json()
        assert "reset_token" in data

    def test_reset_password_success(self, client, db_session):
        """Test reset password endpoint."""
        from src.models.user import User
        from src.services.password_reset_service import PasswordResetService

        user = User(
            id="reset-test-id",
            username="resetuser",
            email="reset@example.com",
            password_hash="old_hashed_password"
        )
        db_session.add(user)
        db_session.commit()

        # Generate a valid token
        service = PasswordResetService()
        token = service.generate_reset_token("reset-test-id")

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
                "email": "reset@example.com",
                "password": "old_hashed_password"
            }
        )
        assert login_response.status_code == 401

        # Verify new password works
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "reset@example.com",
                "password": "NewSecurePass123!"
            }
        )
        assert login_response.status_code == 200

    def test_reset_password_invalid_token(self, client):
        """Test reset password with invalid token."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": "invalid-token",
                "new_password": "NewPassword123!"
            }
        )

        assert response.status_code == 400

    def test_reset_password_missing_fields(self, client):
        """Test reset password with missing fields."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "some-token"}  # missing new_password
        )

        assert response.status_code == 422

    def test_forgot_password_missing_email(self, client):
        """Test forgot password with missing email."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={}
        )

        assert response.status_code == 422
