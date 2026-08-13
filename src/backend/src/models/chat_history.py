"""Chat history model for persistent WebSocket messages."""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import Session
from ..database import Base


class ChatHistory(Base):
    __tablename__ = 'chat_histories'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tutorial_id = Column(String(36), nullable=False, index=True)
    channel_id = Column(String(36), nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # 'user' or 'ai'
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default='message')  # message, typing, system
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def create(db: Session, tutorial_id: str, channel_id: str, sender: str, content: str, message_type: str = 'message') -> 'ChatHistory':
        """Create a chat history record."""
        record = ChatHistory(
            tutorial_id=tutorial_id,
            channel_id=channel_id,
            sender=sender,
            content=content,
            message_type=message_type
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_history(db: Session, tutorial_id: str, channel_id: str, limit: int = 50) -> list:
        """Get chat history for a tutorial channel, ordered by time ascending."""
        return db.query(ChatHistory).filter(
            ChatHistory.tutorial_id == tutorial_id,
            ChatHistory.channel_id == channel_id
        ).order_by(ChatHistory.created_at.asc()).limit(limit).all()

    @staticmethod
    def get_last_message(db: Session, tutorial_id: str, channel_id: str) -> Optional['ChatHistory']:
        """Get the last message for a tutorial channel."""
        return db.query(ChatHistory).filter(
            ChatHistory.tutorial_id == tutorial_id,
            ChatHistory.channel_id == channel_id
        ).order_by(ChatHistory.created_at.desc()).first()
