"""Task logs for tracking background operations."""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, Text, JSON, ForeignKey
from sqlalchemy.orm import Session
from ..database import Base


class TaskLog(Base):
    """Tracks the status and progress of asynchronous tasks."""

    __tablename__ = 'task_logs'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    task_type = Column(SQLEnum("generate_outline", "generate_chapter", "save_config", "publish_tutorial", "delete_tutorial", name='task_type_enum'), nullable=False)
    status = Column(SQLEnum("pending", "running", "success", "failed", "cancelled", name='task_status_enum'), default="pending")
    progress = Column(Integer, default=0)
    result_url = Column(String(1024), nullable=True)
    error_message = Column(Text, nullable=True)
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "task_type": self.task_type,
            "status": self.status,
            "progress": self.progress,
            "result_url": self.result_url,
            "error_message": self.error_message,
            "details": self.details_json,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None
        }

    @staticmethod
    def get_by_id(db: Session, task_id: str) -> 'TaskLog':
        """Get task log by ID."""
        return db.query(TaskLog).filter(TaskLog.id == task_id).first()

    @staticmethod
    def create(db: Session, user_id: str, task_type: str, **kwargs) -> 'TaskLog':
        """Create a new task log."""
        task_log = TaskLog(
            user_id=user_id,
            task_type=task_type,
            **kwargs
        )
        db.add(task_log)
        db.commit()
        db.refresh(task_log)
        return task_log
