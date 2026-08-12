"""Authentication service for user registration and login."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..models.user import User
from ..database import get_db, engine
from ..models.profile import UserProfile

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Secret key and token configuration (should come from env)
SECRET_KEY = "your-secret-key-change-in-production"  # In production, use os.getenv
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class AuthService:
    """Handles authentication operations including token generation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def register(self, username: str, email: str, password: str) -> Dict:
        """Register a new user."""
        # Check if user exists
        existing = self.db.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing:
            raise ValueError("Username or email already exists")
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Create empty profile
        profile = UserProfile(user_id=str(user.id), username=username, email=email)
        self.db.add(profile)
        self.db.commit()
        
        # Create access token
        access_token = self.create_access_token(data={"sub": user.id})
        
        return {
            "user": user.to_dict(),
            "token": access_token,
            "expires_in": ACCESS_TOKEN_EXPIRES_MINUTES * 60
        }
    
    def login(self, email: str, password: str) -> Dict:
        """Authenticate user and return access token."""
        user = self.get_user_by_email(email)
        if not user or not self.verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        
        access_token = self.create_access_token(data={"sub": user.id})
        return {
            "user": user.to_dict(),
            "token": access_token,
            "expires_in": ACCESS_TOKEN_EXPIRES_MINUTES * 60
        }
    
    def get_current_user(self, token: str) -> User:
        """Decode token and retrieve current user."""
        credentials_exception = JWTError("Could not validate credentials")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except JWTError:
            raise credentials_exception
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise credentials_exception
        return user
