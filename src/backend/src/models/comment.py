"""Comment model for tutorial discussions."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Session
from ..database import Base


class Comment(Base):
    __tablename__ = 'tutorial_comments'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String(36), ForeignKey('tutorials.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    parent_id = Column(String(36), ForeignKey('tutorial_comments.id', ondelete='CASCADE'), nullable=True)
    like_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    tutorial = relationship("Tutorial", backref="comments")
    user = relationship("User")
    replies = relationship("Comment", remote_side=[id], cascade="all, delete-orphan", single_parent=True)

    @property
    def is_reply(self) -> bool:
        return self.parent_id is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tutorial_id": self.tutorial_id,
            "user_id": self.user_id,
            "content": self.content,
            "parent_id": self.parent_id,
            "like_count": self.like_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_reply": self.is_reply,
            "user": {
                "id": self.user.id if self.user else None,
                "username": self.user.username if self.user else "Unknown"
            } if self.user else None,
            "replies": [r.to_dict() for r in (self.replies or [])]
        }

    @staticmethod
    def create(db: Session, user_id: str, tutorial_id: str, content: str, parent_id: str = None) -> 'Comment':
        """Create a new comment or reply."""
        comment = Comment(
            user_id=user_id,
            tutorial_id=tutorial_id,
            content=content,
            parent_id=parent_id
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    @staticmethod
    def get_by_tutorial(db: Session, tutorial_id: str) -> list:
        """Get all top-level comments for a tutorial (no replies included)."""
        return db.query(Comment).filter_by(tutorial_id=tutorial_id, parent_id=None).order_by(Comment.created_at.asc()).all()

    @staticmethod
    def get_replies(db: Session, parent_id: str) -> list:
        """Get all replies to a comment."""
        return db.query(Comment).filter_by(parent_id=parent_id).order_by(Comment.created_at.asc()).all()

    @staticmethod
    def like_comment(db: Session, comment_id: str) -> int:
        """Like a comment, return new like_count."""
        comment = db.query(Comment).filter_by(id=comment_id).first()
        if not comment:
            raise ValueError("Comment not found")
        comment.like_count += 1
        db.commit()
        db.refresh(comment)
        return comment.like_count

    @staticmethod
    def delete_comment(db: Session, comment_id: str, user_id: str) -> bool:
        """Delete a comment (only owner or if it's their own)."""
        comment = db.query(Comment).filter_by(id=comment_id).first()
        if not comment or comment.user_id != user_id:
            return False
        db.delete(comment)
        db.commit()
        return True
