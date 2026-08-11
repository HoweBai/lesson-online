"""User knowledge mapping model."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.types import TypeDecorator, JSON
from sqlalchemy.orm import Session
from ..database import Base


class UserKnowledgeMapping(Base):
    __tablename__ = 'user_knowledge_mappings'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, unique=True)
    mastery_map = Column(JSON, nullable=True)
    inferred_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "mastery_map": self.mastery_map,
            "inferred_at": self.inferred_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

    @staticmethod
    def get_by_user(db: Session, user_id: str) -> 'UserKnowledgeMapping':
        """Get knowledge mapping by user ID."""
        return db.query(UserKnowledgeMapping).filter(UserKnowledgeMapping.user_id == user_id).first()
