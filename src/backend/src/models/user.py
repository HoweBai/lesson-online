"""User model for authentication."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, UniqueConstraint, Boolean
from sqlalchemy.orm import Session
from ..database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "is_admin": self.is_admin,
        }

    @staticmethod
    def get_current(db: Session, user_id: str) -> 'User':
        """Get current user by ID."""
        return db.query(User).filter(User.id == user_id).first()
