"""User knowledge mapping model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, JSONB, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP
from .database import Base


class UserKnowledgeMapping(Base):
    """Stores inferred knowledge levels for a user's topics."""
    
    __tablename__ = 'user_knowledge_mappings'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    mastery_map = Column(JSONB, nullable=True)  # e.g., {"algorithm_fundamentals": "intermediate"}
    inferred_at = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP, nullable=True)  # Optional expiration timestamp
    
    def to_dict(self) -> dict:
        """Return knowledge mapping as dict."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "mastery_map": self.mastery_map,
            "inferred_at": self.inferred_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
