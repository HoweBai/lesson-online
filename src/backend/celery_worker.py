"""Celery worker entry point for the Online Learning Platform."""

import os
import logging
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Celery configuration
celery_app = Celery(
    'tasks',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # Results expire after 1 hour
)

# Import tasks
from ..tasks.outline_tasks import generate_outline_task  # noqa: E402
from ..tasks.chapter_tasks import generate_chapter_task  # noqa: E402
from ..tasks.export_tasks import export_file_task         # noqa: E402

if __name__ == '__main__':
    logger.info("Starting Celery worker...")
    celery_app.start()
