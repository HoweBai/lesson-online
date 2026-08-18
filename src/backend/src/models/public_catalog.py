"""Public catalog - manages published tutorials visible to everyone."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship, Session
from ..database import Base


class PublicCatalog(Base):
    """Represents a tutorial that has been published to the public course catalog."""

    __tablename__ = 'public_catalog'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String(36), ForeignKey('tutorials.id'), unique=True, nullable=False)
    published_by = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    publish_time = Column(DateTime, default=datetime.utcnow)
    approved_by = Column(String(36), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    reported_count = Column(Integer, default=0)

    tutorial = relationship("Tutorial", backref="catalog_entry")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tutorial_id": self.tutorial_id,
            "published_by": str(self.published_by),
            "publish_time": self.publish_time.isoformat() if self.publish_time else None,
            "approved_by": str(self.approved_by) if self.approved_by else None,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "reported_count": self.reported_count
        }
