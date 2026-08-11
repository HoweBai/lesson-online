"""User profile model for learning preferences."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Text, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import Session
from ..database import Base


class UserProfile(Base):
    __tablename__ = 'user_profiles'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    programming_level = Column(Integer, nullable=True)  # 1-5
    math_background = Column(Text, nullable=True)
    learning_goal = Column(Text, nullable=True)
    available_hours_per_day = Column(Float, nullable=True)
    preferred_style = Column(String(20), nullable=True)  # visual/text/code/exercise
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "programming_level": self.programming_level,
            "math_background": self.math_background,
            "learning_goal": self.learning_goal,
            "available_hours_per_day": self.available_hours_per_day,
            "preferred_style": self.preferred_style,
            "created_at": self.created_at.isoformat()
        }

    @staticmethod
    def get_by_user(db: Session, user_id: str) -> 'UserProfile':
        """Get user profile by user ID."""
        return db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
