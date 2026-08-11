"""Authentication service for user registration and login."""

import uuid
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional, Dict
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from ..database import get_db
from ..models.user import User
from ..models.profile import UserProfile
import os

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Load secret key from environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class AuthService:
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def register(self, db: Session, username: str, email: str, password: str) -> Dict:
        """Register a new user."""
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            raise ValueError("Username or email already exists")

        user = User(username=username, email=email)
        user.password_hash = self.hash_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)

        profile = UserProfile(
            user_id=str(user.id),
            programming_level=1,
            learning_goal="general",
            preferred_style="text"
        )
        db.add(profile)
        db.commit()

        token = self.create_access_token(data={"sub": str(user.id)})
        return {"user": user.to_dict(), "token": token}

    def login(self, db: Session, email: str, password: str) -> Dict:
        """Login with email and password."""
        user = db.query(User).filter(User.email == email).first()
        if not user or not self.verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        token = self.create_access_token(data={"sub": str(user.id)})
        return {"user": user.to_dict(), "token": token}

    def get_current_user(self, db: Session, token: str) -> User:
        """Get current user from token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
        except JWTError:
            raise ValueError("Could not validate credentials")
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise ValueError("User not found")
        return user


def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    """Dependency to get current authenticated user."""
    auth_service = AuthService()
    return auth_service.get_current_user(db, token)
