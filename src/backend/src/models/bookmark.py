"""Bookmark model for tutorial favorites."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from ..database import Base


class Bookmark(Base):
    __tablename__ = 'user_bookmarks'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    tutorial_id = Column(String(36), ForeignKey('tutorials.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'tutorial_id', name='uq_user_tutorial_bookmark'),
    )

    user = relationship("User", backref="bookmarks")
    tutorial = relationship("Tutorial", backref="bookmarks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tutorial_id": self.tutorial_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @staticmethod
    def create(db: Session, user_id: str, tutorial_id: str) -> 'Bookmark':
        """Create a bookmark, return None if already exists."""
        existing = db.query(Bookmark).filter_by(
            user_id=user_id, tutorial_id=tutorial_id
        ).first()
        if existing:
            return existing
        bookmark = Bookmark(user_id=user_id, tutorial_id=tutorial_id)
        db.add(bookmark)
        db.commit()
        db.refresh(bookmark)
        return bookmark

    @staticmethod
    def delete(db: Session, user_id: str, tutorial_id: str) -> bool:
        """Delete a bookmark. Returns True if deleted, False if not found."""
        bookmark = db.query(Bookmark).filter_by(
            user_id=user_id, tutorial_id=tutorial_id
        ).first()
        if not bookmark:
            return False
        db.delete(bookmark)
        db.commit()
        return True

    @staticmethod
    def is_bookmarked(db: Session, user_id: str, tutorial_id: str) -> bool:
        """Check if a tutorial is bookmarked by a user."""
        return db.query(Bookmark).filter_by(
            user_id=user_id, tutorial_id=tutorial_id
        ).first() is not None

    @staticmethod
    def get_by_user(db: Session, user_id: str, page: int = 1, limit: int = 20) -> dict:
        """Get all bookmarks for a user with pagination."""
        total = db.query(Bookmark).filter_by(user_id=user_id).count()
        offset = (page - 1) * limit
        bookmarks = db.query(Bookmark).filter_by(user_id=user_id).offset(offset).limit(limit).all()
        return {
            "data": [b.to_dict() for b in bookmarks],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
