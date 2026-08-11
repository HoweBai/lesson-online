"""Authentication endpoints for user registration and login."""

from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database import get_db
from ..services.auth_service import AuthService, get_current_user
from ..models.user import User
from pydantic import BaseModel

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Register a new user account."""
    try:
        auth_service = AuthService()
        return auth_service.register(db, request.username, request.email, request.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Login with email and password."""
    try:
        auth_service = AuthService()
        return auth_service.login(db, request.email, request.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@auth_router.post("/logout")
async def logout() -> Dict[str, str]:
    """Simple logout."""
    return {"message": "Logged out successfully"}


@auth_router.get("/me")
async def get_current_user_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> Dict:
    """Get current authenticated user information."""
    return user.to_dict()
