"""Database configuration and session management."""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
import sqlite3
import logging
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for local development, PostgreSQL for production
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ollp.db")

# Configure engine based on database type
if "postgresql" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
else:
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    # Lazy imports to avoid circular dependency
    from src.models.audit_log import AuditLog
    from src.models.bookmark import Bookmark
    from src.models.comment import Comment
    from src.models.chat_history import ChatHistory
    Base.metadata.create_all(bind=engine)


def get_session() -> Session:
    """Get a database session (for use outside of FastAPI dependency injection)."""
    return SessionLocal()


def migrate_db():
    """Run database migrations for new features."""
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute("ALTER TABLE tutorials ADD COLUMN share_code VARCHAR(20) UNIQUE")
            conn.commit()
            print("Added share_code column to tutorials")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_histories (
                    id VARCHAR(36) NOT NULL,
                    tutorial_id VARCHAR(36) NOT NULL,
                    channel_id VARCHAR(36) NOT NULL,
                    sender VARCHAR(20) NOT NULL,
                    content TEXT NOT NULL,
                    message_type VARCHAR(50) DEFAULT 'message',
                    created_at DATETIME,
                    PRIMARY KEY (id)
                )
            """)
            conn.commit()
            print("Created chat_histories table")
        except sqlite3.OperationalError:
            pass  # Table already exists
        conn.close()
