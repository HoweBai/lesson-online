"""OAuth2 authentication service for Google and GitHub providers."""

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy.orm import Session

from ..models.oauth_token import OAuthToken
from ..models.user import User
from ..services.auth_service import AuthService
from ..services.crypto_service import SecureCryptoService

logger = logging.getLogger(__name__)


class OAuthService:
    """OAuth2 authentication service."""

    def __init__(self, crypto_service: SecureCryptoService):
        self.crypto = crypto_service
        self.auth_service = AuthService()
        self.providers: Dict[str, Dict[str, str]] = {}

    def register_google(self, client_id: str, client_secret: str) -> None:
        """Register Google OAuth provider."""
        self.providers['google'] = {
            'client_id': client_id,
            'client_secret': client_secret,
            'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'userinfo_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
            'scopes': ['openid', 'email', 'profile'],
        }

    def register_github(self, client_id: str, client_secret: str) -> None:
        """Register GitHub OAuth provider."""
        self.providers['github'] = {
            'client_id': client_id,
            'client_secret': client_secret,
            'authorize_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'userinfo_url': 'https://api.github.com/user',
            'scopes': ['user:email'],
        }

    def google_authorize_url(self, state: str) -> str:
        """Return Google OAuth authorize URL."""
        return self.get_authorize_url('google', state)

    def github_authorize_url(self, state: str) -> str:
        """Return GitHub OAuth authorize URL."""
        return self.get_authorize_url('github', state)

    def get_authorize_url(self, provider: str, state: str) -> str:
        """Build OAuth authorize URL for a provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not configured")
        p = self.providers[provider]
        redirect_uri = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/{provider}/callback"
        from urllib.parse import urlencode
        params = {
            'client_id': p['client_id'],
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': ' '.join(p['scopes']),
            'state': state,
            'prompt': 'consent',
        }
        return f"{p['authorize_url']}?{urlencode(params)}"

    def google_callback(self, code: str, state: str, db: Session) -> Dict[str, Any]:
        """Exchange code for token and create/login Google user."""
        return self.handle_callback('google', code, state, db)

    def github_callback(self, code: str, state: str, db: Session) -> Dict[str, Any]:
        """Exchange code for token and create/login GitHub user."""
        return self.handle_callback('github', code, state, db)

    def handle_callback(self, provider: str, code: str, state: str, db: Session) -> Dict[str, Any]:
        """Handle OAuth callback — exchange code for token and create/login user."""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not configured")
        p = self.providers[provider]

        # Verify state
        stored_state = db.query(OAuthToken).filter(
            OAuthToken.state == state,
            OAuthToken.provider == provider,
            OAuthToken.expires_at > datetime.now(timezone.utc)
        ).first()
        if not stored_state:
            raise ValueError("Invalid or expired state token")

        # Exchange code for access token
        redirect_uri = f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/{provider}/callback"
        token_resp = httpx.post(
            p['token_url'],
            data={
                'client_id': p['client_id'],
                'client_secret': p['client_secret'],
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': redirect_uri,
            },
            headers={'Accept': 'application/json'}
        )
        token_data = token_resp.json()
        if 'access_token' not in token_data:
            raise ValueError(f"OAuth token exchange failed: {token_data.get('error_description', token_data)}")

        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 3600)

        # Fetch user info
        user_info_resp = httpx.get(
            p['userinfo_url'],
            headers={'Authorization': f'Bearer {access_token}'}
        )
        user_info = user_info_resp.json()

        # Extract email and name
        if provider == 'google':
            email = user_info.get('email', '')
            name = user_info.get('name', user_info.get('email', '').split('@')[0])
            avatar = user_info.get('picture', '')
        else:  # github
            email = user_info.get('email') or self._get_github_emails(access_token).get('primary', '')
            name = user_info.get('name') or user_info.get('login', '')
            avatar = user_info.get('avatar_url', '')

        if not email:
            raise ValueError("Could not retrieve email from provider")

        # Create or find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Auto-create user
            username = name.lower().replace(' ', '_')
            if not username:
                username = f"{provider}_user_{secrets.token_hex(4)}"
            # Ensure unique username
            base_username = username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}_{counter}"
                counter += 1
            user = User(username=username, email=email)
            user.password_hash = self.auth_service.hash_password(secrets.token_hex(32))
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Update avatar if available
            if avatar and not user.avatar_url:
                user.avatar_url = avatar
                db.commit()

        # Store encrypted access token
        encrypted_token = self.crypto.encrypt(access_token)
        existing_token = db.query(OAuthToken).filter(
            OAuthToken.user_id == user.id,
            OAuthToken.provider == provider
        ).first()
        if existing_token:
            existing_token.encrypted_token = encrypted_token
            existing_token.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        else:
            oauth_token = OAuthToken(
                user_id=user.id,
                provider=provider,
                encrypted_token=encrypted_token,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            )
            db.add(oauth_token)
        db.commit()

        # Clean up state
        db.delete(stored_state)
        db.commit()

        # Create JWT token
        jwt_token = self.auth_service.create_access_token(data={"sub": str(user.id)})
        return {
            "user": user.to_dict(),
            "token": jwt_token,
        }

    def _get_github_emails(self, access_token: str) -> Dict[str, Any]:
        """Get primary email from GitHub (secondary emails require extra API calls)."""
        try:
            resp = httpx.get(
                'https://api.github.com/user/emails',
                headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
            )
            emails = resp.json()
            for e in emails:
                if e.get('primary') and e.get('verified'):
                    return {'primary': e['email']}
            if emails:
                return {'primary': emails[0]['email']}
        except Exception as e:
            logger.warning("Failed to fetch GitHub emails: %s", e)
        return {}

    def store_access_token(self, db: Session, user_id: str, provider: str, encrypted_token: str, expires_in: int = 3600) -> None:
        """Persist encrypted access token."""
        record = db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider
        ).first()
        if record:
            record.encrypted_token = encrypted_token
        else:
            record = OAuthToken(
                user_id=user_id,
                provider=provider,
                encrypted_token=encrypted_token,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in / 3600),
            )
            db.add(record)
        db.commit()

    def get_access_token(self, db: Session, user_id: str, provider: str) -> Optional[str]:
        """Retrieve and decrypt stored OAuth access token."""
        record = db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
            OAuthToken.expires_at > datetime.now(timezone.utc)
        ).first()
        if not record:
            return None
        return self.crypto.decrypt(record.encrypted_token)

    def revoke_access(self, db: Session, user_id: str, provider: str) -> bool:
        """Remove stored OAuth access token."""
        record = db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider
        ).first()
        if not record:
            return False
        db.delete(record)
        db.commit()
        return True


def get_oauth_service() -> OAuthService:
    """Create and return the global OAuth service instance."""
    from ..services.crypto_service import SecureCryptoService
    import os
    master_key_hex = os.getenv("CRYPTO_KEY_HEX", "0" * 64)
    master_key = bytes.fromhex(master_key_hex)[:32]
    crypto = SecureCryptoService(master_key)
    service = OAuthService(crypto)

    google_id = os.getenv("GOOGLE_CLIENT_ID")
    google_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if google_id and google_secret:
        service.register_google(google_id, google_secret)
        logger.info("Google OAuth registered")

    github_id = os.getenv("GITHUB_CLIENT_ID")
    github_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if github_id and github_secret:
        service.register_github(github_id, github_secret)
        logger.info("GitHub OAuth registered")

    return service
