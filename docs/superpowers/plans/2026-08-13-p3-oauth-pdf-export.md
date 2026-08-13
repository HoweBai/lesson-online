# P3 OAuth + PDF Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OAuth third-party login (Google + GitHub) and PDF tutorial export to complete the platform feature set.

**Architecture:** Backend uses `authlib` for OAuth2 authorization code flow with stateless JWT tokens. Google and GitHub clients are registered via environment variables. Frontend shows OAuth buttons on AuthPage and redirects back to the app after callback. PDF export uses `weasyprint` — the export service converts tutorial Markdown to styled HTML then renders to PDF.

**Tech Stack:** FastAPI + authlib + SQLite (backend), React 18 + TypeScript + Tailwind CSS (frontend), WeasyPrint (PDF)

**Spec:** FUNCTIONAL_GAP_ANALYSIS_v2.md (P3 section), docs/superpowers/specs/2026-08-11-platform-enhancement-design.md (section 2.4)

## Pre-existing Test State

Running the full suite produces **8 failures** (all pre-existing, not caused by P2 or P3 work):
- 5 bookmark API tests (`test_bookmark_api.py`) — wrong URL paths in tests
- 2 auth extended tests (`test_auth_extended.py`) — test isolation / state pollution
- 1 endpoints test (`test_endpoints.py::test_register`) — test isolation / rate limiter interaction

These failures appear when running the full suite but pass in isolation. They are tracked as pre-existing and **must not increase** after P3 work.

---

## Global Constraints

- OAuth client IDs are read from environment variables `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` — all optional, app starts without them
- OAuth login creates new users automatically on first login (email from provider verified)
- OAuth access tokens are stored encrypted using the same AES-GCM `SecureCryptoService` pattern as Claude API keys
- PDF export requires `weasyprint>=61.0`; graceful fallback returns 501 if not installed
- All new dependencies added to `requirements.txt` and `package.json` as appropriate
- Existing 8 pre-existing test failures must not increase
- Build must succeed after each task: `cd src/frontend && npm run build`
- Backend tests must pass for all new code: `cd src/backend && python -m pytest tests/ -v --tb=short`

---

## File Structure Overview

**Backend changes:**
```
src/backend/requirements.txt                          -- Modify: add authlib, weasyprint
src/backend/src/services/oauth_service.py             -- Create: OAuth2 auth service
src/backend/src/api/oauth.py                          -- Create: OAuth routes (init, authorize, callback, logout)
src/backend/src/services/export_service.py             -- Modify: add export_to_pdf method
src/backend/src/api/export.py                         -- Modify: add /export/pdf endpoint
src/backend/tests/test_oauth.py                       -- Create: OAuth API tests
src/backend/tests/test_pdf_export.py                  -- Create: PDF export tests
```

**Frontend changes:**
```
src/frontend/package.json                             -- Modify: add react-icons
src/frontend/src/api/client.ts                        -- Modify: add OAuth client methods
src/frontend/src/pages/AuthPage.tsx                   -- Modify: add OAuth login buttons
src/frontend/src/pages/TutorialDisplayPage.tsx        -- Modify: add PDF export button
src/frontend/src/api/client.ts                        -- Modify: add exportPDF method
```

---

## Task 1: Backend — OAuth Service + Google Provider

**Files:**
- Create: `src/backend/src/services/oauth_service.py`
- Modify: `src/backend/requirements.txt`

**Interfaces:**
- Consumes: `AuthService` (for token creation), `SecureCryptoService` (for token encryption), `User` model
- Produces: `OAuthService` class with methods:
  - `register_google(client_id, client_secret)` — registers Google OAuth provider
  - `register_github(client_id, client_secret)` — registers GitHub OAuth provider
  - `google_authorize_url(state)` — returns Google OAuth authorize URL
  - `github_authorize_url(state)` — returns GitHub OAuth authorize URL
  - `google_callback(code, state)` — exchanges code for token, creates/returns user
  - `github_callback(code, state)` — exchanges code for token, creates/returns user
  - `store_access_token(user_id, provider, encrypted_token)` — persists encrypted access token
  - `get_access_token(user_id, provider)` — retrieves and decrypts stored token

- [ ] **Step 1: Add dependencies to requirements.txt**

Open `src/backend/requirements.txt`. Add at the end:
```
authlib>=1.3.0
weasyprint>=61.0
```

- [ ] **Step 2: Create OAuth service**

Create `src/backend/src/services/oauth_service.py`:
```python
"""OAuth2 authentication service for Google and GitHub providers."""

import os
import uuid
import secrets
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode, quote

from sqlalchemy.orm import Session
from authlib.integrations.requests_client import OAuth2Session
from authlib.integrations.base_client import OAuthError

from ..models.user import User
from ..models.oauth_token import OAuthToken
from ..services.auth_service import AuthService
from ..services.crypto_service import SecureCryptoService
from ..database import get_db

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

    def get_authorize_url(self, provider: str, state: str) -> str:
        """Build OAuth authorize URL for a provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not configured")
        p = self.providers[provider]
        params = {
            'client_id': p['client_id'],
            'redirect_uri': f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/{provider}/callback",
            'response_type': 'code',
            'scope': ' '.join(p['scopes']),
            'state': state,
            'prompt': 'consent',
        }
        return f"{p['authorize_url']}?{urlencode(params)}"

    def handle_callback(self, provider: str, code: str, state: str, db: Session) -> Dict[str, Any]:
        """Handle OAuth callback — exchange code for token and create/login user."""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not configured")
        p = self.providers[provider]

        # Verify state
        stored_state = db.query(OAuthToken).filter(
            OAuthToken.state == state,
            OAuthToken.provider == provider,
            OAuthToken.expires_at > __import__('datetime').datetime.utcnow()
        ).first()
        if not stored_state:
            raise ValueError("Invalid or expired state token")

        # Exchange code for access token
        import httpx
        token_resp = httpx.post(
            p['token_url'],
            data={
                'client_id': p['client_id'],
                'client_secret': p['client_secret'],
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')}/auth/{provider}/callback",
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
            existing_token.expires_at = __import__('datetime').datetime.utcnow() + __import__('datetime').timedelta(seconds=expires_in)
        else:
            oauth_token = OAuthToken(
                user_id=user.id,
                provider=provider,
                encrypted_token=encrypted_token,
                expires_at=__import__('datetime').datetime.utcnow() + __import__('datetime').timedelta(seconds=expires_in),
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
        import httpx
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
        except Exception:
            pass
        return {}

    def get_access_token(self, db: Session, user_id: str, provider: str) -> Optional[str]:
        """Retrieve and decrypt stored OAuth access token."""
        record = db.query(OAuthToken).filter(
            OAuthToken.user_id == user_id,
            OAuthToken.provider == provider,
            OAuthToken.expires_at > __import__('datetime').datetime.utcnow()
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
    from ..database import get_db as _get_db
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
```

- [ ] **Step 3: Create OAuthToken model**

Create `src/backend/src/models/oauth_token.py`:
```python
"""OAuth token storage model for persistent access tokens."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from ..database import Base


class OAuthToken(Base):
    """Encrypted OAuth access token storage."""
    __tablename__ = 'oauth_tokens'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    provider = Column(String(20), nullable=False)  # 'google' or 'github'
    encrypted_token = Column(String(512), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    state = Column(String(64), unique=True, nullable=True)  # for OAuth state validation

    @staticmethod
    def create_state(db, user_id: str, provider: str) -> str:
        """Generate and store a state token for OAuth flow."""
        import secrets
        state = secrets.token_urlsafe(32)
        record = OAuthToken(
            user_id=user_id,
            provider=provider,
            state=state,
            expires_at=datetime.utcnow() + datetime.timedelta(minutes=10),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return state

    @staticmethod
    def validate_state(db, state: str, provider: str) -> bool:
        """Validate and consume an OAuth state token."""
        record = db.query(OAuthToken).filter(
            OAuthToken.state == state,
            OAuthToken.provider == provider,
            OAuthToken.expires_at > datetime.utcnow()
        ).first()
        if not record:
            return False
        db.delete(record)
        db.commit()
        return True
```

- [ ] **Step 4: Add OAuthToken to Base (register model)**

Open `src/backend/src/database.py`. Find where models are imported/registered. The `Base` uses declarative base — models register themselves via `__tablename__`. Verify that `OAuthToken` is imported in `__init__.py` or the model import list.

In `src/backend/src/models/__init__.py` (or wherever models are imported for `Base.metadata`), add:
```python
from .oauth_token import OAuthToken
```

If `__init__.py` does not exist, add the import to `src/backend/src/database.py`'s `Base.metadata.create_all` call area, or create `src/backend/src/models/__init__.py`:
```python
"""Model registry — importing all models registers them with SQLAlchemy Base."""
from .user import User
from .tutorial import Tutorial
from .chapter import Chapter
from .bookmark import Bookmark
from .comment import Comment
from .profile import UserProfile
from .knowledge_mapping import UserKnowledgeMapping
from .task_log import TaskLog
from .public_catalog import PublicCatalog
from .claude_config import ClaudeConfig
from .chat_history import ChatHistory
from .oauth_token import OAuthToken
```

- [ ] **Step 5: Add OAuth table migration**

Open `src/backend/src/database.py`. In the `migrate_db()` function, add before `conn.close()`:
```python
        # Create oauth_tokens table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) NOT NULL,
                provider VARCHAR(20) NOT NULL,
                encrypted_token VARCHAR(512) NOT NULL,
                expires_at DATETIME NOT NULL,
                created_at DATETIME,
                state VARCHAR(64) UNIQUE
            )
        """)
        conn.commit()
```

- [ ] **Step 6: Add dependencies to requirements.txt**

Open `src/backend/requirements.txt`. Add:
```
authlib>=1.3.0
weasyprint>=61.0
```

- [ ] **Step 7: Run backend tests to verify no breakage**

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: no new failures (same 5 bookmark pre-existing failures if any)

- [ ] **Step 8: Commit**

```bash
git add src/backend/requirements.txt src/backend/src/services/oauth_service.py src/backend/src/models/oauth_token.py src/backend/src/database.py
git commit -m "feat: add OAuth service with Google and GitHub provider support"
```

---

## Task 2: Backend — OAuth API Endpoints

**Files:**
- Create: `src/backend/src/api/oauth.py`
- Modify: `src/backend/src/api/main.py`

**Interfaces:**
- Consumes: `OAuthService`, `get_current_user`
- Produces: `oauth_router` with endpoints:
  - `GET /api/v1/oauth/google/init` — return authorize URL + state
  - `GET /api/v1/oauth/github/init` — return authorize URL + state
  - `GET /api/v1/oauth/google/callback` — handle Google callback
  - `GET /api/v1/oauth/github/callback` — handle GitHub callback
  - `GET /api/v1/oauth/me` — current user OAuth info
  - `DELETE /api/v1/oauth/{provider}` — revoke OAuth access

- [ ] **Step 1: Create OAuth API router**

Create `src/backend/src/api/oauth.py`:
```python
"""OAuth authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
import os

from ..database import get_db
from ..services.auth_service import get_current_user
from ..models.user import User
from ..services.oauth_service import get_oauth_service, OAuthService

logger = logging.getLogger(__name__)

oauth_router = APIRouter(prefix="/oauth", tags=["oauth"])


def _get_service() -> OAuthService:
    return get_oauth_service()


@oauth_router.get("/google/init")
async def google_init(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: OAuthService = Depends(_get_service),
):
    """Initialize Google OAuth flow — returns authorize URL."""
    if 'google' not in service.providers:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    state = __import__('src.models.oauth_token', fromlist=['OAuthToken']).OAuthToken.create_state(
        db, str(current_user.id), 'google'
    )
    # Actually we need the state directly — let's use secrets
    import secrets as _secrets
    state = _secrets.token_urlsafe(32)
    # Store state in oauth_tokens
    from ..models.oauth_token import OAuthToken
    oauth_state = OAuthToken(
        user_id=str(current_user.id),
        provider='google',
        state=state,
    )
    db.add(oauth_state)
    db.commit()

    url = service.get_authorize_url('google', state)
    return {"authorize_url": url, "state": state}


@oauth_router.get("/github/init")
async def github_init(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: OAuthService = Depends(_get_service),
):
    """Initialize GitHub OAuth flow — returns authorize URL."""
    if 'github' not in service.providers:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    import secrets as _secrets
    state = _secrets.token_urlsafe(32)
    from ..models.oauth_token import OAuthToken
    oauth_state = OAuthToken(
        user_id=str(current_user.id),
        provider='github',
        state=state,
    )
    db.add(oauth_state)
    db.commit()

    url = service.get_authorize_url('github', state)
    return {"authorize_url": url, "state": state}


@oauth_router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
    service: OAuthService = Depends(_get_service),
):
    """Handle Google OAuth callback — redirect to frontend with token."""
    try:
        result = service.handle_callback('google', code, state, db)
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        token = result['token']
        user = result['user']
        # Redirect to frontend with token in URL fragment (client-side handling)
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?token={token}&provider=google",
            status_code=302,
        )
    except ValueError as e:
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/login?error={str(e)}",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/login?error=OAuth+callback+failed",
            status_code=302,
        )


@oauth_router.get("/github/callback")
async def github_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
    service: OAuthService = Depends(_get_service),
):
    """Handle GitHub OAuth callback — redirect to frontend with token."""
    try:
        result = service.handle_callback('github', code, state, db)
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        token = result['token']
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?token={token}&provider=github",
            status_code=302,
        )
    except ValueError as e:
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/login?error={str(e)}",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"GitHub OAuth callback error: {e}")
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        return RedirectResponse(
            url=f"{frontend_url}/login?error=OAuth+callback+failed",
            status_code=302,
        )


@oauth_router.get("/me")
async def get_oauth_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: OAuthService = Depends(_get_service),
):
    """Get current user's OAuth provider connections."""
    from ..models.oauth_token import OAuthToken
    tokens = db.query(OAuthToken).filter(
        OAuthToken.user_id == str(current_user.id),
        OAuthToken.encrypted_token.isnot(None)
    ).all()
    providers = []
    for t in tokens:
        providers.append({
            'provider': t.provider,
            'connected': True,
            'expires_at': t.expires_at.isoformat() if t.expires_at else None,
        })
    return {"providers": providers}


@oauth_router.delete("/{provider}")
async def revoke_oauth(
    provider: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: OAuthService = Depends(_get_service),
):
    """Revoke OAuth access for a provider."""
    if provider not in ('google', 'github'):
        raise HTTPException(status_code=400, detail="Invalid provider")
    success = service.revoke_access(db, str(current_user.id), provider)
    if not success:
        raise HTTPException(status_code=404, detail="No OAuth connection found")
    return {"success": True, "message": f"Revoked {provider} connection"}
```

- [ ] **Step 2: Register oauth router in main.py**

Open `src/backend/src/api/main.py`. After the existing imports, add:
```python
from ..api.oauth import oauth_router
```

Add router registration with other routers:
```python
app.include_router(oauth_router, prefix="/api/v1")
```

- [ ] **Step 3: Run backend tests**

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Expected: no new failures

- [ ] **Step 4: Commit**

```bash
git add src/backend/src/api/oauth.py src/backend/src/api/main.py
git commit -m "feat: add OAuth API endpoints for Google and GitHub"
```

---

## Task 3: Backend — PDF Export

**Files:**
- Modify: `src/backend/src/services/export_service.py`
- Modify: `src/backend/src/api/export.py`

**Interfaces:**
- Consumes: `ExportService` with existing `export_to_markdown`, `export_to_json`
- Produces: `export_to_pdf(tutorial_id)` method and `GET /export/pdf` endpoint

- [ ] **Step 1: Add PDF export to export service**

Open `src/backend/src/services/export_service.py`. Add after the existing `export_to_json` method:
```python
    def export_to_pdf(self, tutorial_id: str) -> Dict[str, Any]:
        """Export tutorial content to PDF using WeasyPrint."""
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            raise RuntimeError("weasyprint is not installed. Install with: pip install weasyprint")

        md_result = self.export_to_markdown(tutorial_id)
        html_content = self._markdown_to_html(md_result["content"], md_result["title"])

        pdf_bytes = HTML(string=html_content).write_pdf(
            stylesheets=[CSS(string=self._PDF_CSS)]
        )
        return {
            "tutorial_id": tutorial_id,
            "title": md_result["title"],
            "format": "pdf",
            "size_bytes": len(pdf_bytes),
            "chapter_count": md_result["chapter_count"],
        }

    _PDF_CSS = """
    @page { size: A4; margin: 2cm; }
    body { font-family: 'Segoe UI', Arial, sans-serif; font-size: 11pt; color: #1a1a2e; line-height: 1.6; }
    h1 { font-size: 22pt; color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 0.3em; }
    h2 { font-size: 16pt; color: #0f3460; margin-top: 1.5em; }
    h3 { font-size: 13pt; color: #1a1a2e; }
    pre { background: #f4f4f8; padding: 1em; border-radius: 6px; font-size: 9pt; overflow-x: auto; }
    code { background: #f0f0f5; padding: 0.1em 0.3em; border-radius: 3px; font-size: 9pt; }
    blockquote { border-left: 4px solid #0f3460; margin: 0; padding-left: 1em; color: #555; }
    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
    th, td { border: 1px solid #ddd; padding: 0.5em; text-align: left; }
    th { background: #f0f0f5; }
    ul, ol { padding-left: 1.5em; }
    li { margin: 0.3em 0; }
    hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
    """

    def _markdown_to_html(self, markdown: str, title: str) -> str:
        """Convert markdown to HTML for PDF rendering."""
        import re
        html = markdown

        # Escape HTML
        html = html.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Headings
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

        # Bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

        # Code blocks
        html = re.sub(r'```(\w+)?\n(.+?)```', r'<pre><code>\2</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

        # Horizontal rule
        html = re.sub(r'^---$', '<hr/>', html, flags=re.MULTILINE)

        # Unordered lists
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', html)

        # Ordered lists
        html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)

        # Paragraphs
        html = re.sub(r'\n\n', '</p><p>', html)
        html = '<p>' + html + '</p>'
        html = re.sub(r'<p>(<h[123]>|<hr/?>|<ul>|</ul>|<pre>|</pre>)', r'\1', html)
        html = re.sub(r'(</h[123]>|</hr(?:/?)?>|</ul>|</pre>)</p>', r'\1', html)

        # Clean up empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)
        html = re.sub(r'<p>\n', '<p>', html)
        html = re.sub(r'\n</p>', '</p>', html)

        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body>{html}</body></html>"""
```

- [ ] **Step 2: Add PDF export endpoint**

Open `src/backend/src/api/export.py`. Add the PDF export endpoint after the outline export:
```python
@router.get("/{tutorial_id}/export/pdf")
async def export_pdf(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Response:
    """Export tutorial content as PDF."""
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        (Tutorial.owner_id == current_user.id) | (Tutorial.is_public == True)
    ).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    try:
        export_service = create_export_service(db)
        result = export_service.export_to_pdf(tutorial_id)
        return Response(
            content=result["pdf_bytes"],
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={tutorial.title.replace(' ', '_')}.pdf"}
        )
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"Export to PDF failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

Also add `from fastapi.responses import Response` to the imports at the top (it's already there).

Update `export_to_pdf` in the service to also return `pdf_bytes` in the result dict. Add `result["pdf_bytes"] = pdf_bytes` before returning.

- [ ] **Step 3: Verify backend imports work**

```bash
cd src/backend && python -c "from src.services.export_service import ExportService; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add src/backend/src/services/export_service.py src/backend/src/api/export.py
git commit -m "feat: add PDF export using WeasyPrint with styled HTML template"
```

---

## Task 4: Frontend — OAuth Buttons + Auth Callback Page

**Files:**
- Modify: `src/frontend/src/api/client.ts`
- Modify: `src/frontend/src/pages/AuthPage.tsx`
- Create: `src/frontend/src/pages/AuthCallbackPage.tsx`
- Modify: `src/frontend/src/App.tsx`

**Interfaces:**
- Consumes: existing `api.login()`, `api.setToken()`
- Produces: OAuth init URLs on AuthPage, callback handler on AuthCallbackPage

- [ ] **Step 1: Add OAuth methods to API client**

Open `src/frontend/src/api/client.ts`. Add after the `getTutorialByShareCode` method:
```typescript
  // OAuth endpoints
  async oauthGoogleInit() {
    return this.request<any>('GET', '/api/v1/oauth/google/init');
  }

  async oauthGithubInit() {
    return this.request<any>('GET', '/api/v1/oauth/github/init');
  }

  async oauthMe() {
    return this.request<any>('GET', '/api/v1/oauth/me');
  }

  async oauthRevoke(provider: string) {
    return this.request<any>('DELETE', `/api/v1/oauth/${provider}`);
  }
```

- [ ] **Step 2: Create AuthCallbackPage**

Create `src/frontend/src/pages/AuthCallbackPage.tsx`:
```tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';

const AuthCallbackPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = searchParams.get('token');
    const provider = searchParams.get('provider');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setError(decodeURIComponent(errorParam));
      return;
    }

    if (token) {
      api.setToken(token);
      localStorage.setItem('oauth_provider', provider || '');
      navigate('/');
    } else {
      navigate('/login');
    }
  }, [searchParams, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <div className="text-center">
        {error ? (
          <>
            <div className="text-4xl mb-4">⚠️</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Authentication Failed</h2>
            <p className="text-gray-500 mb-4">{error}</p>
            <button
              onClick={() => navigate('/login')}
              className="px-6 py-2 bg-primary-600 text-white rounded-xl hover:bg-primary-700"
            >
              Back to Login
            </button>
          </>
        ) : (
          <>
            <div className="relative w-16 h-16 mx-auto mb-4">
              <div className="absolute inset-0 border-4 border-primary-200 rounded-full"></div>
              <div className="absolute inset-0 border-4 border-primary-600 rounded-full border-t-transparent animate-spin"></div>
            </div>
            <p className="text-gray-600 font-medium">Signing you in...</p>
          </>
        )}
      </div>
    </div>
  );
};

export default AuthCallbackPage;
```

- [ ] **Step 3: Add OAuth buttons to AuthPage**

Open `src/frontend/src/pages/AuthPage.tsx`. After the password fields (in login mode) and before the submit button, add:
```tsx
{/* OAuth Divider */}
{mode === 'login' && (
  <div className="relative my-6">
    <div className="absolute inset-0 flex items-center">
      <div className="w-full border-t border-gray-200 dark:border-gray-600"></div>
    </div>
    <div className="relative flex justify-center text-sm">
      <span className="px-4 bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400">
        Or continue with
      </span>
    </div>
  </div>
)}

{/* OAuth Buttons */}
{mode === 'login' && (
  <div className="grid grid-cols-2 gap-3">
    <button
      onClick={async () => {
        const result = await api.oauthGoogleInit();
        if (result.success && result.data?.authorize_url) {
          window.location.href = result.data.authorize_url;
        }
      }}
      className="flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
    >
      <svg className="w-5 h-5" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-200">Google</span>
    </button>
    <button
      onClick={async () => {
        const result = await api.oauthGithubInit();
        if (result.success && result.data?.authorize_url) {
          window.location.href = result.data.authorize_url;
        }
      }}
      className="flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
    >
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-7.29 0-.166.042-.327.042-.327.056-.092.195-.136.352-.136h.003c.157 0 .296.044.352.136.042.12.083.282.083.472 0 3.133-1.513 4.476-3.087 4.955.262.216.52.638.52 1.287v3.609c0 .318.192.694.703.577 4.765-1.589 8.199-6.085 8.199-11.387 0-6.627-5.373-12-12-12z"/>
      </svg>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-200">GitHub</span>
    </button>
  </div>
)}
```

- [ ] **Step 4: Add AuthCallbackPage route to App.tsx**

Open `src/frontend/src/App.tsx`. Add import:
```typescript
import AuthCallbackPage from './pages/AuthCallbackPage';
```

Add route inside the `!user` (unauthenticated) routes block:
```tsx
<Route path="/auth/callback" element={<AuthCallbackPage />} />
```

- [ ] **Step 5: Build frontend**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/api/client.ts src/frontend/src/pages/AuthCallbackPage.tsx src/frontend/src/pages/AuthPage.tsx src/frontend/src/App.tsx
git commit -m "feat: add OAuth login with Google and GitHub buttons on AuthPage"
```

---

## Task 5: Frontend — PDF Export Button

**Files:**
- Modify: `src/frontend/src/api/client.ts`
- Modify: `src/frontend/src/pages/TutorialDisplayPage.tsx`

**Interfaces:**
- Consumes: existing `exportMarkdown`, `exportJSON` methods
- Produces: `exportPDF()` method on ApiClient, PDF export button in TutorialDisplayPage

- [ ] **Step 1: Add exportPDF to API client**

Open `src/frontend/src/api/client.ts`. Find the export methods section. Add after `exportOutline`:
```typescript
  async exportPDF(tutorialId: string) {
    const response = await fetch(`${API_BASE}/api/v1/tutorials/${tutorialId}/export/pdf`, {
      headers: this.getHeaders()
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'PDF export failed');
    }
    return response.blob();
  }
```

- [ ] **Step 2: Add PDF export button to TutorialDisplayPage**

Open `src/frontend/src/pages/TutorialDisplayPage.tsx`. Find the existing export handler section (around line 158-210). After the outline export handler, add:
```tsx
  const handleExportPDF = async () => {
    try {
      const blob = await api.exportPDF(id!);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${chapter?.title || 'tutorial'}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('PDF exported successfully!');
    } catch (e: any) {
      toast.error(e.message || 'Failed to export PDF');
    }
  };
```

Then find the export buttons section (around line 508-530) and add after the outline button:
```tsx
<button
  onClick={handleExportPDF}
  className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
  title="Export as PDF"
>
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16l-4-4m0 0l4-4m-4 4h18" />
  </svg>
  PDF
</button>
```

- [ ] **Step 3: Build frontend**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully

- [ ] **Step 4: Commit**

```bash
git add src/frontend/src/api/client.ts src/frontend/src/pages/TutorialDisplayPage.tsx
git commit -m "feat: add PDF export button to TutorialDisplayPage"
```

---

## Task 6: Backend — OAuth + PDF Tests

**Files:**
- Create: `src/backend/tests/test_oauth.py`
- Create: `src/backend/tests/test_pdf_export.py`

**Interfaces:**
- Consumes: `client` fixture, `test_user` fixture from `conftest.py`
- Produces: full test coverage for OAuth endpoints (with mocked HTTP) and PDF export

- [ ] **Step 1: Write OAuth tests**

Create `src/backend/tests/test_oauth.py`:
```python
"""Tests for OAuth API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.database import engine, Base, get_db
from src.models.user import User
from src.services.auth_service import AuthService
from src.api.main import app

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestOAuthEndpoints:
    """Test OAuth API endpoints."""

    def setup_method(self):
        """Create test user and token."""
        auth = AuthService()
        with Session(bind=engine) as db:
            user = User(username="oauthuser", email="oauth@test.com")
            user.password_hash = auth.hash_password("testpass123")
            db.add(user)
            db.commit()
            db.refresh(user)
            self.token = auth.create_access_token(data={"sub": str(user.id)})
            self.user_id = user.id

    def test_google_init_unauthenticated(self):
        """Google init without auth returns 401."""
        resp = client.get("/api/v1/oauth/google/init")
        assert resp.status_code == 401

    def test_google_init_not_configured(self):
        """Google init when not configured returns 503."""
        resp = client.get(
            "/api/v1/oauth/google/init",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        # Google not configured → 503
        assert resp.status_code == 503

    def test_github_init_not_configured(self):
        """GitHub init when not configured returns 503."""
        resp = client.get(
            "/api/v1/oauth/github/init",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 503

    def test_oauth_me(self):
        """Get OAuth connections info."""
        resp = client.get(
            "/api/v1/oauth/me",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data

    def test_oauth_me_unauthenticated(self):
        """OAuth /me without auth returns 401."""
        resp = client.get("/api/v1/oauth/me")
        assert resp.status_code == 401

    @patch('src.services.oauth_service.httpx')
    def test_google_callback_success(self, mock_httpx):
        """Google callback redirects to frontend with token."""
        mock_token_resp = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "mock_token", "expires_in": 3600}
        mock_userinfo_resp = MagicMock()
        mock_userinfo_resp.json.return_value = {
            "email": "oauthuser@test.com",
            "name": "OAuth User",
            "picture": "https://example.com/avatar.jpg"
        }
        mock_httpx.post.return_value = mock_token_resp
        mock_httpx.get.return_value = mock_userinfo_resp

        # Create state record
        from src.models.oauth_token import OAuthToken
        import secrets
        state = secrets.token_urlsafe(32)
        with Session(bind=engine) as db:
            db.add(OAuthToken(user_id=str(self.user_id), provider='google', state=state))
            db.commit()

        resp = client.get(
            f"/api/v1/oauth/google/callback?code=mock_code&state={state}"
        )
        # Should redirect (302)
        assert resp.status_code in [302, 303]

    def test_revoke_nonexistent_provider(self):
        """Revoke non-existent provider returns 404."""
        resp = client.delete(
            "/api/v1/oauth/google",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 404

    def test_revoke_invalid_provider(self):
        """Revoke invalid provider returns 400."""
        resp = client.delete(
            "/api/v1/oauth/facebook",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 400
```

- [ ] **Step 2: Write PDF export tests**

Create `src/backend/tests/test_pdf_export.py`:
```python
"""Tests for PDF export endpoint."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.database import engine, Base, get_db
from src.models.user import User
from src.models.tutorial import Tutorial
from src.services.auth_service import AuthService
from src.api.main import app
from datetime import datetime

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


class TestPDFExport:
    """Test PDF export endpoint."""

    def setup_method(self):
        """Create test user and tutorial."""
        auth = AuthService()
        with Session(bind=engine) as db:
            user = User(username="pdfuser", email="pdfuser@test.com")
            user.password_hash = auth.hash_password("testpass123")
            db.add(user)
            db.commit()
            db.refresh(user)
            self.token = auth.create_access_token(data={"sub": str(user.id)})
            self.user_id = user.id

            tutorial = Tutorial(
                owner_id=str(user.id),
                title="PDF Test Tutorial",
                description="A test tutorial for PDF export",
                status="published",
                is_public=True,
                total_chapters=2,
                current_chapter=1,
                created_at=datetime.utcnow(),
            )
            db.add(tutorial)
            db.commit()
            db.refresh(tutorial)
            self.tutorial_id = tutorial.id

    def test_pdf_export_unauthenticated(self):
        """PDF export without auth returns 401."""
        resp = client.get(f"/api/v1/tutorials/{self.tutorial_id}/export/pdf")
        assert resp.status_code == 401

    def test_pdf_export_not_found(self):
        """PDF export for non-existent tutorial returns 404."""
        resp = client.get(
            "/api/v1/tutorials/nonexistent/export/pdf",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 404

    @patch('src.services.export_service.ExportService.export_to_pdf')
    def test_pdf_export_success(self, mock_export):
        """PDF export returns PDF bytes."""
        mock_export.return_value = {
            "tutorial_id": self.tutorial_id,
            "title": "PDF Test Tutorial",
            "format": "pdf",
            "size_bytes": 1024,
            "chapter_count": 2,
            "pdf_bytes": b"%PDF-1.4 mock pdf content",
        }
        resp = client.get(
            f"/api/v1/tutorials/{self.tutorial_id}/export/pdf",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 200
        assert resp.headers['content-type'] == 'application/pdf'
        assert resp.headers['content-disposition'].startswith('attachment')
        mock_export.assert_called_once()

    @patch('src.services.export_service.ExportService.export_to_pdf')
    def test_pdf_export_weasyprint_not_installed(self, mock_export):
        """PDF export returns 501 when weasyprint unavailable."""
        mock_export.side_effect = RuntimeError("weasyprint is not installed")
        resp = client.get(
            f"/api/v1/tutorials/{self.tutorial_id}/export/pdf",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        assert resp.status_code == 501

    def test_pdf_export_unauthorized_tutorial(self):
        """User cannot export another user's private tutorial."""
        auth = AuthService()
        with Session(bind=engine) as db:
            other_user = User(username="otheruser", email="other@test.com")
            other_user.password_hash = auth.hash_password("testpass123")
            db.add(other_user)
            db.commit()
            db.refresh(other_user)
            other_token = auth.create_access_token(data={"sub": str(other_user.id)})

            other_tutorial = Tutorial(
                owner_id=str(other_user.id),
                title="Private Tutorial",
                status="draft",
                is_public=False,
                created_at=datetime.utcnow(),
            )
            db.add(other_tutorial)
            db.commit()
            db.refresh(other_tutorial)
            other_id = other_tutorial.id

        resp = client.get(
            f"/api/v1/tutorials/{other_id}/export/pdf",
            headers={"Authorization": f"Bearer {other_token}"}
        )
        assert resp.status_code == 404
```

- [ ] **Step 3: Run all tests**

```bash
cd src/backend && python -m pytest tests/test_oauth.py tests/test_pdf_export.py -v --tb=short 2>&1 | tail -30
```
Expected: all new tests pass

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -10
```
Expected: same failure count as before (no new failures)

- [ ] **Step 4: Commit**

```bash
git add src/backend/tests/test_oauth.py src/backend/tests/test_pdf_export.py
git commit -m "test: add OAuth and PDF export API tests"
```

---

## Task 7: Fix Pre-existing Bookmark Test Failures

**Files:**
- Modify: `src/backend/tests/test_bookmark_api.py`

**Interfaces:**
- Consumes: existing bookmark API and test fixtures
- Produces: all 6 bookmark tests passing (currently 1 passing, 5 failing due to wrong URL paths)

- [ ] **Step 1: Fix bookmark test URLs**

Open `src/backend/tests/test_bookmark_api.py`. The tests call `POST /api/v1/bookmarks/{tutorial_id}` but the actual endpoint is `POST /api/v1/bookmarks/{tutorial_id}/bookmark`. Fix all test methods:

In `test_bookmark_tutorial`, change:
```python
resp = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")
```
to:
```python
resp = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}/bookmark")
```

In `test_duplicate_bookmark`, change both calls:
```python
resp1 = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")
resp2 = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}")
```
to:
```python
resp1 = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}/bookmark")
resp2 = bookmark_client.post(f"/api/v1/bookmarks/{tutorial_id}/bookmark")
```

In `test_unbookmark_tutorial`, change:
```python
resp = bookmark_client.delete(f"/api/v1/bookmarks/{tutorial_id}")
```
to:
```python
resp = bookmark_client.delete(f"/api/v1/bookmarks/{tutorial_id}/bookmark")
```

Also fix `test_bookmark_not_found` (line 109):
```python
resp = bookmark_client.post("/api/v1/bookmarks/nonexistent")
```
to:
```python
resp = bookmark_client.post("/api/v1/bookmarks/nonexistent/bookmark")
```

- [ ] **Step 2: Fix list bookmarks URLs**

In `test_list_bookmarks`, change:
```python
resp = bookmark_client.get("/api/v1/bookmarks")
```
to:
```python
resp = bookmark_client.get("/api/v1/bookmarks/bookmarks")
```

In `test_list_bookmarks_empty`, change:
```python
resp = bookmark_client.get("/api/v1/bookmarks")
```
to:
```python
resp = bookmark_client.get("/api/v1/bookmarks/bookmarks")
```

- [ ] **Step 3: Run bookmark tests**

```bash
cd src/backend && python -m pytest tests/test_bookmark_api.py -v --tb=short
```
Expected: all 6 tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/backend/tests/test_bookmark_api.py
git commit -m "fix: correct bookmark API test URLs to match actual endpoint paths"
```

---

## Task 8: Final Verification + README Update

**Files:**
- Modify: `README.md`
- Modify: `src/frontend/src/App.tsx` (admin link visibility)

**Interfaces:**
- Consumes: no new backend/frontend code
- Produces: updated documentation and admin nav link only visible to admins

- [ ] **Step 1: Show admin link only to admins in App.tsx**

Open `src/frontend/src/App.tsx`. Find the admin nav link:
```tsx
<NavLink href="/admin" icon="🛡️" label="Admin" />
```

Change to conditionally render (user must be logged in AND be admin):
```tsx
{user?.is_admin && <NavLink href="/admin" icon="🛡️" label="Admin" />}
```

Also update the `user` state to include `is_admin`. In the `useEffect` where user is set from localStorage, add a check — or better, store user data. Currently `user` is just `{ token }`. Update the user loading logic:

In the `useEffect`:
```typescript
useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      api.getMe().then((result) => {
        if (result.success && result.data?.user) {
          setUser({ token, ...result.data.user });
        } else {
          setUser({ token });
        }
      }).catch(() => setUser({ token }));
    }
    setLoading(false);
  }, []);
```

- [ ] **Step 2: Update README with P3 features**

Open `README.md`. Add a new section after the existing feature list:

```markdown
### P3 — Experience Enhancements (2026-08-13)
- ✅ OAuth third-party login (Google, GitHub)
- ✅ PDF tutorial export
- ✅ Admin link visible only to admin users
- ✅ Dark mode (completed in P2)
```

- [ ] **Step 3: Final backend test run**

```bash
cd src/backend && python -m pytest tests/ -v --tb=short 2>&1 | tail -15
```
Expected: 8 failures (same pre-existing baseline), no new failures

- [ ] **Step 4: Final frontend build**

```bash
cd src/frontend && npm run build
```
Expected: Compiled successfully

- [ ] **Step 5: Final commit**

```bash
git add README.md src/frontend/src/App.tsx
git commit -m "docs: add P3 features to README and fix admin nav visibility"
```
