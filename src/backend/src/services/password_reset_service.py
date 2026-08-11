"""Password reset service using JWT tokens."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt

from ..models.user import User
from ..database import SessionLocal
from .auth_service import pwd_context, SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRE_HOURS = 1


class PasswordResetService:
    """Service for handling password reset via JWT tokens."""

    def generate_reset_token(self, user_id: str) -> str:
        """
        Generate a password reset token for a user.

        Args:
            user_id: The user's UUID string

        Returns:
            JWT token string that expires in RESET_TOKEN_EXPIRE_HOURS
        """
        expire = datetime.utcnow() + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": user_id,
            "type": "password_reset",
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    def decode_token(self, token: str) -> Optional[Dict]:
        """
        Decode and validate a password reset token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != "password_reset":
                return None
            # Check if user still exists
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == payload.get("sub")).first()
                if not user:
                    return None
                return payload
            finally:
                db.close()
        except JWTError:
            return None

    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset user's password using a valid token.

        Args:
            token: Valid password reset JWT token
            new_password: New plain text password

        Returns:
            True if password was reset successfully, False otherwise
        """
        payload = self.decode_token(token)
        if not payload:
            logger.warning("Invalid or expired password reset token used")
            return False

        user_id = payload["sub"]
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False

            user.password_hash = pwd_context.hash(new_password)
            db.commit()
            logger.info(f"Password reset successful for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Password reset failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()
