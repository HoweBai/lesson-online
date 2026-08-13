"""Tests for OAuth API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database import engine, Base, get_db
from src.services.auth_service import AuthService
from src.models.user import User
from src.models.oauth_token import OAuthToken


Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def _get_auth_token(client_email: str = "oauthuser@test.com") -> str:
    """Create and return a JWT token for the test user."""
    auth = AuthService()
    with Session(bind=engine) as db:
        user = db.query(User).filter(User.email == client_email).first()
        if not user:
            result = auth.register(db, "oauthuser", client_email, "testpass123")
            token = result["token"]
        else:
            token = auth.create_access_token(data={"sub": str(user.id)})
    return token


def _create_oauth_token(db: Session, user_id: str, provider: str, encrypted_token: str = "encrypted") -> OAuthToken:
    """Helper to insert an OAuth token record."""
    from datetime import datetime, timezone, timedelta
    record = OAuthToken(
        user_id=user_id,
        provider=provider,
        encrypted_token=encrypted_token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _cleanup_oauth_tokens():
    """Remove all oauth_tokens records for a clean slate."""
    with Session(bind=engine) as db:
        db.query(OAuthToken).delete()
        db.commit()


class TestGoogleInit:
    """Test Google OAuth init endpoint."""

    @pytest.fixture
    def client(self):
        token = _get_auth_token()
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_google_init_returns_url_and_state(self, client):
        """Test Google init returns authorize URL and state."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.providers = {'google': {}, 'github': {}}
            mock_service.get_authorize_url.return_value = "https://accounts.google.com/o/oauth2/v2/auth?state=abc"
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/oauth/google/init")
            assert response.status_code == 200
            data = response.json()
            assert "authorize_url" in data
            assert "state" in data
            assert data["authorize_url"].startswith("https://accounts.google.com")

    def test_google_init_503_when_not_configured(self, client):
        """Test Google init returns 503 when not configured."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.providers = {}
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/oauth/google/init")
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"].lower()

    def test_google_init_requires_auth(self):
        """Test Google init requires authentication."""
        c = TestClient(app)
        response = c.get("/api/v1/oauth/google/init")
        assert response.status_code == 401


class TestGithubInit:
    """Test GitHub OAuth init endpoint."""

    @pytest.fixture
    def client(self):
        token = _get_auth_token()
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_github_init_returns_url_and_state(self, client):
        """Test GitHub init returns authorize URL and state."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.providers = {'google': {}, 'github': {}}
            mock_service.get_authorize_url.return_value = "https://github.com/login/oauth/authorize?state=abc"
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/oauth/github/init")
            assert response.status_code == 200
            data = response.json()
            assert "authorize_url" in data
            assert "state" in data
            assert data["authorize_url"].startswith("https://github.com/login/oauth/authorize")

    def test_github_init_503_when_not_configured(self, client):
        """Test GitHub init returns 503 when not configured."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.providers = {}
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/oauth/github/init")
            assert response.status_code == 503

    def test_github_init_requires_auth(self):
        """Test GitHub init requires authentication."""
        c = TestClient(app)
        response = c.get("/api/v1/oauth/github/init")
        assert response.status_code == 401


class TestGoogleCallback:
    """Test Google OAuth callback endpoint."""

    def test_callback_success_redirects(self):
        """Test successful callback redirects to frontend."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.handle_callback.return_value = {
                "user": {"id": "1", "username": "testuser"},
                "token": "jwt-token-xyz",
            }
            mock_get_service.return_value = mock_service

            c = TestClient(app, follow_redirects=False)
            response = c.get("/api/v1/oauth/google/callback", params={"code": "auth-code", "state": "state-123"})
            assert response.status_code == 302
            assert "auth/callback?token=" in response.headers["location"]

    def test_callback_invalid_state_redirects_to_login(self):
        """Test invalid state redirects to login with error."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.handle_callback.side_effect = ValueError("Invalid or expired state token")
            mock_get_service.return_value = mock_service

            c = TestClient(app, follow_redirects=False)
            response = c.get("/api/v1/oauth/google/callback", params={"code": "bad-code", "state": "bad-state"})
            assert response.status_code == 302
            assert "login?error=" in response.headers["location"]

    def test_callback_missing_params_returns_422(self):
        """Test callback without required params returns 422."""
        c = TestClient(app)
        response = c.get("/api/v1/oauth/google/callback")
        assert response.status_code == 422


class TestGithubCallback:
    """Test GitHub OAuth callback endpoint."""

    def test_callback_success_redirects(self):
        """Test successful callback redirects to frontend."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.handle_callback.return_value = {
                "user": {"id": "1", "username": "testuser"},
                "token": "jwt-token-xyz",
            }
            mock_get_service.return_value = mock_service

            c = TestClient(app, follow_redirects=False)
            response = c.get("/api/v1/oauth/github/callback", params={"code": "auth-code", "state": "state-123"})
            assert response.status_code == 302
            assert "auth/callback?token=" in response.headers["location"]

    def test_callback_missing_params_returns_422(self):
        """Test callback without required params returns 422."""
        c = TestClient(app)
        response = c.get("/api/v1/oauth/github/callback")
        assert response.status_code == 422


class TestOauthMe:
    """Test GET /oauth/me endpoint."""

    @pytest.fixture
    def client(self):
        token = _get_auth_token()
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_returns_empty_list_when_no_connections(self, client):
        """Test /me returns empty providers list when user has no connections."""
        _cleanup_oauth_tokens()

        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            response = client.get("/api/v1/oauth/me")
            assert response.status_code == 200
            data = response.json()
            assert "providers" in data
            assert data["providers"] == []

    def test_returns_connected_providers(self, client):
        """Test /me returns connected providers."""
        _cleanup_oauth_tokens()

        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            # Insert OAuth token records
            with Session(bind=engine) as db:
                from datetime import datetime, timezone, timedelta
                user = db.query(User).filter(User.email == "oauthuser@test.com").first()
                _create_oauth_token(db, str(user.id), "google", "enc-token-1")
                _create_oauth_token(db, str(user.id), "github", "enc-token-2")

            response = client.get("/api/v1/oauth/me")
            assert response.status_code == 200
            data = response.json()
            assert len(data["providers"]) == 2
            providers = {p["provider"] for p in data["providers"]}
            assert providers == {"google", "github"}
            for p in data["providers"]:
                assert p["connected"] is True
                assert p["expires_at"] is not None

    def test_requires_auth(self):
        """Test /me requires authentication."""
        c = TestClient(app)
        response = c.get("/api/v1/oauth/me")
        assert response.status_code == 401


class TestRevokeOauth:
    """Test DELETE /oauth/{provider} endpoint."""

    @pytest.fixture
    def client(self):
        token = _get_auth_token()
        c = TestClient(app)
        c.headers["Authorization"] = f"Bearer {token}"
        return c

    def test_revoke_google_success(self, client):
        """Test revoking Google OAuth connection."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.revoke_access.return_value = True
            mock_get_service.return_value = mock_service

            response = client.delete("/api/v1/oauth/google")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Revoked google" in data["message"]

    def test_revoke_github_success(self, client):
        """Test revoking GitHub OAuth connection."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.revoke_access.return_value = True
            mock_get_service.return_value = mock_service

            response = client.delete("/api/v1/oauth/github")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Revoked github" in data["message"]

    def test_revoke_invalid_provider_returns_400(self, client):
        """Test revoking invalid provider returns 400."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service

            response = client.delete("/api/v1/oauth/facebook")
            assert response.status_code == 400
            assert "Invalid provider" in response.json()["detail"]

    def test_revoke_not_connected_returns_404(self, client):
        """Test revoking unconnected provider returns 404."""
        with patch('src.api.oauth.get_oauth_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.revoke_access.return_value = False
            mock_get_service.return_value = mock_service

            response = client.delete("/api/v1/oauth/google")
            assert response.status_code == 404
            assert "No OAuth connection found" in response.json()["detail"]

    def test_revoke_requires_auth(self):
        """Test revoke requires authentication."""
        c = TestClient(app)
        response = c.delete("/api/v1/oauth/google")
        assert response.status_code == 401
