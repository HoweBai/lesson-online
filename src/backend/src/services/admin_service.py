"""Admin authentication and authorization service."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models.user import User
from ..services.auth_service import get_current_user, AuthService


class AdminService:
    """Service for admin authentication and authorization."""

    def __init__(self):
        self.auth_service = AuthService()

    def require_admin(
        self,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        """Check that the current user is an admin."""
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        return current_user

    def admin_login(self, db: Session, email: str, password: str) -> dict:
        """Admin login — same as regular login but requires is_admin=True."""
        auth_service = AuthService()
        user = db.query(User).filter(User.email == email).first()
        if not user or not auth_service.verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        if not user.is_admin:
            raise ValueError("Admin access required")
        token = auth_service.create_access_token(data={"sub": str(user.id)})
        return {"user": user.to_dict(), "token": token}


admin_service = AdminService()
