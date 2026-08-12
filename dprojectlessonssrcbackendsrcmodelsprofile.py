"""User profile model for learning preferences."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Text, Boolean, Integer, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base


class UserProfile(Base):
    """User profile containing learning-related information."""
    
    __tablename__ = 'user_profiles'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    programming_level = Column(Integer, nullable=True)  # 1-5 scale
    math_background = Column(Text, nullable=True)
    learning_goal = Column(Text, nullable=True)
    available_hours_per_day = Column(Float, nullable=True)
    preferred_style = Column(String(20), nullable=True)  # visual/text/code/exercise
    created_at = Column(DateTime, default=datetime.utcnow)
    
    UNIQUECONSTRAINT = UniqueConstraint('user_id', name='uq_user_id')
    
    def to_dict(self) -> dict:
        """Convert profile to dictionary."""
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
