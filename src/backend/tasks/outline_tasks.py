"""Celery task for outline generation."""

import os
import uuid
from datetime import datetime
from typing import Dict, Any

from celery import shared_task
from sqlalchemy.orm import Session

from ...database import SessionLocal
from ...services.outline_generator import OutlineGenerator
from ...services.claude_config_service import ClaudeConfigService
from ...services.crypto_service import SecureCryptoService
from ...models.task_log import TaskLog
from ...models.user_profile import UserProfile
from ...models.knowledge_mapping import UserKnowledgeMapping


@shared_task(bind=True, name='tasks.outline.generate')
def generate_outline_task(
    self,
    task_id: str,
    config_id: str,
    user_id: str,
    topics: list,
) -> Dict[str, Any]:
    """Asynchronous outline generation task."""
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

        # Generate outline (progress 50%)
        task_log.progress = 50
        db.commit()

        generator = OutlineGenerator(db, crypto, config_service)
        result = generator.generate(
            config_id=uuid.UUID(config_id),
            user_id=uuid.UUID(user_id),
            topics=topics,
            mastery_map=mastery_map,
        )

        # Check if cancelled during generation
        if task_log.status == "cancelled":
            return {"status": "cancelled", "task_id": task_id}

        # Extract outline data
        outline_data = result.get("outline", {})
        security_scan = outline_data.get('_security_scan', {})

        # Update task log (progress 100%)
        task_log.status = "success"
        task_log.progress = 100
        task_log.details_json = outline_data
        task_log.finished_at = datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "task_id": task_id,
            "outline": outline_data,
            "needs_review": security_scan.get('needs_review', False),
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
