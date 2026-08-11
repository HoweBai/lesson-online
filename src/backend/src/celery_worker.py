#!/usr/bin/env python3
"""Celery worker entry point for the Online Learning Platform.

Start this worker to process async AI generation tasks:
    $ celery -A backend.src.tasks.generation_tasks worker --loglevel=info -E
"""

from celery import Celery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/platform")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create engine and session factory
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize Celery app
celery_app = Celery(
    "generation_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Configure serializer
celery_app.conf.task_serializer = 'json'
celery_app.conf.result_serializer = 'json'
celery_app.conf.accept_content = ['json']
celery_app.conf.time_limit = 300  # Max 5 minutes per task
celery_app.conf.beat_schedule = {
    # Scheduled tasks here (e.g., purge old task logs)
}

# Import tasks to register them
from src.tasks.generation_tasks import *  # noqa: F401, F403

def get_db():
    """Dependency for database sessions in tasks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

celery_app.conf.localvars = {'get_db': get_db}

if __name__ == '__main__':
    # For development, you can run directly:
    # python -m celery -A worker.app worker --loglevel=info
    pass
