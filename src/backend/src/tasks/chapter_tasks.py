"""Celery task for chapter generation."""

import os
import uuid
from datetime import datetime
from typing import Dict, Any

from celery import shared_task
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..services.chapter_generator import ChapterGenerator
from ..services.claude_config_service import ClaudeConfigService
from ..services.crypto_service import SecureCryptoService
from ..models.task_log import TaskLog
from ..models.profile import UserProfile
from ..models.knowledge_mapping import UserKnowledgeMapping
from ..models.chapter import Chapter
from ..models.tutorial import Tutorial


@shared_task(bind=True, name='tasks.chapter.generate')
def generate_chapter_task(
    self,
    task_id: str,
    config_id: str,
    user_id: str,
    tutorial_id: str,
    chapter_number: int,
    outline_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Asynchronous chapter generation task."""
    db: Session = SessionLocal()
    try:
        # Update task status to running
        task_log = db.query(TaskLog).filter_by(id=task_id).first()
        if not task_log:
            raise ValueError(f"Task {task_id} not found")

        task_log.status = "running"
        task_log.started_at = datetime.utcnow()
        task_log.progress = 10
        db.commit()

        # Check if task was cancelled
        if task_log.status == "cancelled":
            return {"status": "cancelled", "task_id": task_id}

        # Set up services
        master_key_hex = os.getenv("CRYPTO_KEY_HEX")
        master_key = bytes.fromhex(master_key_hex)[:32] if master_key_hex else b"\x00" * 32
        crypto = SecureCryptoService(master_key)
        config_service = ClaudeConfigService(crypto, db)

        # Get user profile and knowledge map
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        profile_dict = profile.to_dict() if profile else {}

        km_record = db.query(UserKnowledgeMapping).filter_by(user_id=user_id).first()
        mastery_map = km_record.mastery_map if km_record and km_record.mastery_map else {}

        # Generate chapter (progress 50%)
        task_log.progress = 50
        db.commit()

        generator = ChapterGenerator(db, crypto, config_service)
        result = generator.generate(
            config_id=uuid.UUID(config_id),
            user_id=uuid.UUID(user_id),
            tutorial_id=uuid.UUID(tutorial_id),
            chapter_number=chapter_number,
            outline_data=outline_data,
            mastery_map=mastery_map,
        )

        # Check if cancelled during generation
        if task_log.status == "cancelled":
            return {"status": "cancelled", "task_id": task_id}

        # Save chapter to database
        chapter_content = result.get("chapter_content", {})
        chapter = Chapter(
            id=str(uuid.uuid4()),
            tutorial_id=tutorial_id,
            chapter_number=chapter_number,
            title=chapter_content.get("chapter_title", f"Chapter {chapter_number}"),
            content=chapter_content,
            status="ready",
            prerequisite_check_passed=result.get("prerequisite_check_passed", True),
            generated_at=datetime.utcnow(),
        )
        db.add(chapter)

        # Update tutorial progress
        tutorial = db.query(Tutorial).filter_by(id=tutorial_id).first()
        if tutorial:
            tutorial.current_chapter = chapter_number + 1

        db.commit()

        # Update task log (progress 100%)
        task_log.status = "success"
        task_log.progress = 100
        task_log.details_json = {"chapter_id": chapter.id, "chapter_number": chapter_number}
        task_log.finished_at = datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "task_id": task_id,
            "chapter_id": chapter.id,
            "chapter_number": chapter_number,
            "title": chapter.title,
        }

    except Exception as e:
        # Mark task as failed
        task_log = db.query(TaskLog).filter_by(id=task_id).first()
        if task_log:
            task_log.status = "failed"
            task_log.error_message = str(e)
            task_log.finished_at = datetime.utcnow()
            db.commit()
        raise

    finally:
        db.close()
