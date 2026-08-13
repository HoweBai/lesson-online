"""OAuth authentication API endpoints for Google and GitHub."""

import logging
import os
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.oauth_token import OAuthToken
from ..models.user import User
from ..services.auth_service import get_current_user
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
    """Initialize Google OAuth flow -- returns authorize URL."""
    if 'google' not in service.providers:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    state = secrets.token_urlsafe(32)
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
    """Initialize GitHub OAuth flow -- returns authorize URL."""
    if 'github' not in service.providers:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured")
    state = secrets.token_urlsafe(32)
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
    """Handle Google OAuth callback -- redirect to frontend with token."""
    try:
        result = service.handle_callback('google', code, state, db)
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        token = result['token']
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
    """Handle GitHub OAuth callback -- redirect to frontend with token."""
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
    tokens = db.query(OAuthToken).filter(
        OAuthToken.user_id == str(current_user.id),
        OAuthToken.encrypted_token.isnot(None),
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
