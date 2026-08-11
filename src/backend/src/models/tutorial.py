"""Tutorial model for the learning platform."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship, Session
from ..database import Base


class Tutorial(Base):
    """Represents a user-generated tutorial course."""

    __tablename__ = 'tutorials'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    status = Column(SQLEnum('draft', 'reviewing', 'published', 'retired'), default='draft')
    outline = Column(JSON, nullable=True)
    total_chapters = Column(Integer, nullable=True)
    current_chapter = Column(Integer, nullable=True, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chapters = relationship("Chapter", back_populates="tutorial", cascade="all, delete-orphan")

    def to_dict(self, include_outline: bool = False) -> dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "title": self.title,
            "description": self.description,
            "is_public": self.is_public,
            "status": self.status,
            "total_chapters": self.total_chapters,
            "current_chapter": self.current_chapter,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "outline": self.outline if include_outline else None
        }

    @staticmethod
    def get_by_id(db: Session, tutorial_id: str) -> 'Tutorial':
        """Get tutorial by ID."""
        return db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()

    @staticmethod
    def get_by_owner(db: Session, owner_id: str) -> list:
        """Get all tutorials by owner."""
        return db.query(Tutorial).filter(Tutorial.owner_id == owner_id).all()
