"""Celery tasks for asynchronous AI content generation."""

from celery import Celery
from typing import Dict, Any, List
import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session

# Initialize Celery app (should match backend setup)
celery = Celery('generation_tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/1')
celery.conf.task_serializer = 'json'
celery.conf.result_serializer = 'json'
celery.conf.accept_content = ['json']

# Import local modules (these will be available in the worker environment)
# from backend.src.models.tutorial import Tutorial
# from backend.src.services.claudefile_service import ClaudeConfigService
# from backend.src.services.llm_adapter import ClaudeAdapter
# from backend.src.services.prerequisite_checker import PrerequisiteChecker
# from backend.src.services.knowledge_inferencer import DynamicKnowledgeInferencer


@celery.task(bind=True, max_retries=3)
def generate_outline_task(self, user_id: str, profile_id: str,
                           claude_config_id: str, topics: List[str]) -> Dict[str, Any]:
    """Celery task to generate a course outline asynchronously.

    This task runs in the background and returns the generated outline when complete.
    Progress can be tracked through TaskLogs.
    """
    from database import get_db
    from services.claudefile_service import ClaudeConfigService
    from crypto_service import SecureCryptoService
    from services.knowledge_inferencer import DynamicKnowledgeInferencer
    from services.prerequisite_checker import PrerequisiteChecker
    from services.outline_generator import OutlineGenerator
    from models.user import User
    from models.profile import UserProfile
    from models.claudefile import ClaudeConfig
    from models.knowledge_mapping import UserKnowledgeMapping
    from models.task_log import TaskLog

    db_session = None
    try:
        # Get database session
        db_session = get_db()

        # Load crypto service (master key from env)
        from os import environ
        master_key = bytes.fromhex(environ.get('CRYPTO_KEY_HEX', '0'*64))
        crypto_service = SecureCryptoService(master_key)

        # Initialize services
        claude_service = ClaudeConfigService(crypto_service, db_session)

        # Verify user and config ownership
        config = db_session.query(ClaudeConfig).filter_by(id=claude_config_id).first()
        if not config or config.user_id != user_id:
            raise ValueError("Unauthorized access to configuration")

        # Get profile
        profile = db_session.query(UserProfile).filter_by(user_id=profile_id).first()
        if not profile:
            raise ValueError("Profile not found")

        # Infer knowledge map
        inferencer = DynamicKnowledgeInferencer()
        mastery_map = inferencer.infer_knowledge_graph({
            "programming_level": profile.programming_level,
            "math_background": profile.math_background,
            "learning_goal": profile.learning_goal,
            "available_hours_per_day": profile.available_hours_per_day,
            "preferred_style": profile.preferred_style
        })

        # Create outline generator
        generator = OutlineGenerator(db_session, crypto_service, claude_service)

        # Generate outline
        result = generator.generate(
            config_id=uuid.UUID(claude_config_id),
            user_id=user_id,
            topics=topics,
            mastery_map=mastery_map
        )

        # Save to database
        tutorial = Tutorial(owner_id=user_id, title=result["outline"].get("course_title", "New Tutorial"),
                           outline=result["outline"], status="draft")
        db_session.add(tutorial)
        db_session.commit()

        # Update task log
        task_log = TaskLog(
            user_id=user_id,
            task_type="generate_outline",
            status="success",
            progress=100,
            result_url=f"/api/v1/tutorials/{tutorial.id}",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow()
        )
        db_session.add(task_log)
        db_session.commit()

        return {
            "status": "success",
            "tutorial_id": tutorial.id,
            "outline": result["outline"],
            "knowledge_map": mastery_map
        }

    except Exception as e:
        # Log error and retry if applicable
        error_msg = str(e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=self.backoff_function(self.request.retries))
        else:
            # Final failure - log it
            db_session.add(TaskLog(
                user_id=user_id,
                task_type="generate_outline",
                status="failed",
                error_message=error_msg,
                created_at=datetime.utcnow()
            ))
            db_session.commit()
            raise
    finally:
        if db_session:
            db_session.close()


@celery.task(bind=True, max_retries=3)
def generate_chapter_task(self, tutorial_id: str, chapter_number: int,
                          user_id: str, claude_config_id: str,
                          outline_id: str) -> Dict[str, Any]:
    """Celery task to generate a single tutorial chapter asynchronously."""
    from database import get_db
    from services.claudefile_service import ClaudeConfigService
    from crypto_service import SecureCryptoService
    from services.chapter_generator import ChapterGenerator
    from models.chapter import Chapter

    db_session = None
    try:
        db_session = get_db()

        # Setup
        from os import environ
        master_key = bytes.fromhex(environ.get('CRYPTO_KEY_HEX', '0'*64))
        crypto_service = SecureCryptoService(master_key)
        claude_service = ClaudeConfigService(crypto_service, db_session)
        chapter_gen = ChapterGenerator(db_session, crypto_service, claude_service)

        # Fetch tutorial to verify ownership
        tutorial = db_session.query(Tutorial).filter_by(id=tutorial_id, owner_id=user_id).first()
        if not tutorial:
            raise ValueError("Tutorial not found or unauthorized")

        # Fetch outline to determine topic
        outline_db = db_session.query(Tutorial).filter_by(id=outline_id).first()
        if not outline_db:
            raise ValueError("Outline not found")

        # Get user's knowledge mapping (or infer fresh)
        knowledge_map_record = db_session.query(UserKnowledgeMapping).filter_by(user_id=user_id).first()
        if knowledge_map_record and knowledge_map_record.mastery_map:
            mastery_map = knowledge_map_record.mastery_map
        else:
            # Infer fresh (would call inferencer in real code)
            mastery_map = {"algorithm_fundamentals": "beginner", "data_structures": "beginner"}

        # Generate chapter
        result = chapter_gen.generate(
            config_id=uuid.UUID(claude_config_id),
            user_id=user_id,
            tutorial_id=uuid.UUID(tutorial_id),
            chapter_number=chapter_number,
            outline_data=outline_db.outline,
            mastery_map=mastery_map
        )

        # Create chapter record
        chapter = Chapter(
            tutorial_id=tutorial_id,
            chapter_number=chapter_number,
            title=result.get("chapter_number", ""),
            content=result["chapter_content"],
            status="ready",
            prerequisite_check_passed=result.get("prerequisite_review_needed", False) is False,
            generated_at=datetime.utcnow()
        )
        db_session.add(chapter)
        db_session.commit()

        # Update task log and send WebSocket notification (pseudo-code)
        task_log = TaskLog(
            user_id=user_id,
            task_type="generate_chapter",
            status="success",
            progress=100,
            result_url=f"/api/v1/tutorials/{tutorial_id}/chapters/{chapter_number}",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow()
        )
        db_session.add(task_log)
        db_session.commit()

        # In production, publish to Redis channel here:
        # redis.publish(f"chapter:{tutorial_id}:generated", json.dumps({"chapter": chapter_number}))

        return {
            "status": "success",
            "chapter_id": chapter.id,
            "chapter_number": chapter_number
        }

    except Exception as e:
        error_msg = str(e)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=self.backoff_function(self.request.retries))
        else:
            db_session.add(TaskLog(
                user_id=user_id,
                task_type="generate_chapter",
                status="failed",
                error_message=error_msg,
                created_at=datetime.utcnow()
            ))
            db_session.commit()
            raise
    finally:
        if db_session:
            db_session.close()


@celery.task(bind=True, max_retries=2) def refresh_mastery_cache(self, user_id: str):
    """Periodically refresh a user's knowledge mapping from their latest activities."""
    # Implementation would track user interactions and re-infer periodically
    pass
