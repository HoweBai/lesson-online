"""Stores encrypted Claude API configuration."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, LargeBinary
from sqlalchemy.orm import Session
from ..database import Base


class ClaudeConfig(Base):
    __tablename__ = 'claude_configs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(LargeBinary(1024), nullable=False)
    model_name = Column(String(50), nullable=True)
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    is_default = Column(Boolean, default=False)

    def to_dict(self, include_api_key=False):
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "base_url": self.base_url,
            "model_name": self.model_name,
            "system_prompt": self.system_prompt,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "is_default": self.is_default
        }
        return result

    @staticmethod
    def get_by_user(db: Session, user_id: str) -> 'ClaudeConfig':
        """Get user's Claude config."""
        return db.query(ClaudeConfig).filter(ClaudeConfig.user_id == user_id).first()

    @staticmethod
    def get_by_id(db: Session, config_id: str) -> 'ClaudeConfig':
        """Get config by ID."""
        return db.query(ClaudeConfig).filter(ClaudeConfig.id == config_id).first()
