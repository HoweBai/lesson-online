"""Authentication endpoints for user registration and login."""

from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from sqlalchemy.orm import Session
from typing import Dict, Any

from ..database import get_db
from ..services.auth_service import AuthService, get_current_user
from ..models.user import User
from ..middleware.rate_limiter import limiter
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
@limiter.limit("5/minute")
async def register(
    request: Request,
    request_body: RegisterRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Register a new user account."""
    try:
        auth_service = AuthService()
        return auth_service.register(db, request_body.username, request_body.email, request_body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@auth_router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    request_body: LoginRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Login with email and password."""
    try:
        auth_service = AuthService()
        return auth_service.login(db, request_body.email, request_body.password)
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
    return {"user": user.to_dict()}
