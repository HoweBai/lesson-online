"""OAuth token storage model for persistent access tokens."""

import uuid
from datetime import datetime, timedelta, timezone
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
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
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
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
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
            OAuthToken.expires_at > datetime.now(timezone.utc)
        ).first()
        if not record:
            return False
        db.delete(record)
        db.commit()
        return True
