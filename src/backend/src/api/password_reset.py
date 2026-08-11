"""Password reset API endpoints."""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Any
import logging
from datetime import datetime, timedelta
from jose import jwt

from ..services.password_reset_service import PasswordResetService
from ..models.user import User
from ..database import SessionLocal
from ..services.auth_service import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["password-reset"])


class ForgotPasswordRequest(BaseModel):
    """Request for password reset token."""
    email: str = Field(..., description="User's email address")


class ResetPasswordRequest(BaseModel):
    """Request to reset password with token."""
    token: str = Field(..., description="Password reset JWT token")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest
) -> Dict[str, Any]:
    """
    Generate a password reset token for the given email.
    Always returns 200 to prevent email enumeration.
    """
    service = PasswordResetService()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == request.email).first()
        if user:
            reset_token = service.generate_reset_token(str(user.id))
            logger.info(f"Password reset token generated for user {user.id}")
            return {
                "message": "Password reset token generated",
                "reset_token": reset_token,
                "expires_in_hours": 1
            }
    finally:
        db.close()

    # Return a fake token anyway to prevent email enumeration
    expire = datetime.utcnow() + timedelta(hours=1)
    fake_token = jwt.encode({
        "sub": "non-existent",
        "type": "password_reset",
        "exp": expire
    }, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "message": "Password reset token generated",
        "reset_token": fake_token,
        "expires_in_hours": 1
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest
) -> Dict[str, str]:
    """
    Reset user's password using the provided token.
    """
    service = PasswordResetService()
    success = service.reset_password(request.token, request.new_password)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    return {"message": "Password reset successful"}
