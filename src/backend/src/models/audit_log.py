"""Audit log model for tracking security scans and user actions."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.orm import Session
from ..database import Base


class AuditLog(Base):
    """Records user actions and system events for audit purposes."""

    __tablename__ = 'audit_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    action_type = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)
    success = Column(DateTime, default=datetime.utcnow)
    details_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action_type": self.action_type,
            "ip_address": self.ip_address,
            "success": self.success.isoformat() if self.success else None,
            "details": self.details_json,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

    @staticmethod
    def create(db: Session, user_id: str, action_type: str, details: dict = None, ip_address: str = None) -> 'AuditLog':
        """Create a new audit log entry."""
        log = AuditLog(
            user_id=user_id,
            action_type=action_type,
            ip_address=ip_address,
            details_json=details
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
