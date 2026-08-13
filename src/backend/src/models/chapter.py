"""Chapter model for tutorial content."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, JSON, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship, Session
from ..database import Base


class Chapter(Base):
    """A single chapter within a tutorial course."""

    __tablename__ = 'chapters'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String(36), ForeignKey('tutorials.id'), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(JSON, nullable=True)
    status = Column(SQLEnum('draft', 'ready', 'in_progress', 'completed', 'failed', name='chapter_status'), default='draft')
    prerequisite_check_passed = Column(Boolean, default=False)
    generated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1)

    tutorial = relationship("Tutorial", back_populates="chapters")

    def to_dict(self, include_content: bool = True) -> dict:
        result = {
            "id": self.id,
            "tutorial_id": self.tutorial_id,
            "chapter_number": self.chapter_number,
            "title": self.title,
            "status": self.status,
            "prerequisite_check_passed": self.prerequisite_check_passed,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "version": self.version
        }
        if include_content and self.content:
            result["content"] = self.content
        return result

    @staticmethod
    def get_by_tutorial(db: Session, tutorial_id: str) -> list:
        """Get all chapters for a tutorial."""
        return db.query(Chapter).filter(Chapter.tutorial_id == tutorial_id).order_by(Chapter.chapter_number).all()

    @staticmethod
    def get_by_number(db: Session, tutorial_id: str, chapter_number: int) -> 'Chapter':
        """Get a specific chapter by number."""
        return db.query(Chapter).filter(
            Chapter.tutorial_id == tutorial_id,
            Chapter.chapter_number == chapter_number
        ).first()
