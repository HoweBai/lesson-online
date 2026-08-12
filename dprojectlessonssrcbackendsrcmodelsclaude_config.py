"""Claude API configuration model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, DateTime, Binary, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from .database import Base


class ClaudeConfig(Base):
    """Stores encrypted Claude API configuration."""
    
    __tablename__ = 'claude_configs'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    base_url = Column(String(500), nullable=False)
    api_key_encrypted = Column(Binary(1024), nullable=False)  # Encrypted key
    model_name = Column(String(50), nullable=True)
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    is_default = Column(Boolean, default=False)
    
    UNIQUECONSTRAINT = UniqueConstraint('user_id', name='uq_claude_user_id')
    
    def to_dict(self, include_api_key: bool = False) -> dict:
        """Convert config to dictionary. Do NOT include API key unless explicitly requested."""
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
        if include_api_key:
            # Decryption would be handled by service layer
            pass
        return result
