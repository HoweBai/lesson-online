"""Tutorial API endpoints with full implementation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import logging
import json
import os

from ..database import get_db
from ..services.auth_service import get_current_user
from ..models.user import User
from ..models.tutorial import Tutorial
from ..models.chapter import Chapter
from ..models.claude_config import ClaudeConfig
from ..models.task_log import TaskLog
from ..models.knowledge_mapping import UserKnowledgeMapping
from ..models.profile import UserProfile
from ..schemas.api import (
    GenerateOutlineRequest, OutlineStatusResponse, ConfirmOutlineRequest,
    GenerateNextChapterRequest, ChapterStatusResponse, TutorialSummary,
    TutorialDetail, ChapterSummary, TaskLogSummary, ClaudeConfigRequest,
    ClaudeConfigResponse, TutorialStatus, ChapterStatus, OutlineStatus
)
from ..services.outline_generator import OutlineGenerator
from ..services.chapter_generator import ChapterGenerator
from ..services.claude_config_service import ClaudeConfigService
from ..services.crypto_service import SecureCryptoService
from fastapi import Query

logger = logging.getLogger(__name__)

tutorials_router = APIRouter(prefix="/tutorials", tags=["tutorials"])

# Service instances
_crypto_service: Optional[SecureCryptoService] = None
_claude_config_service: Optional[ClaudeConfigService] = None


def get_crypto_service() -> SecureCryptoService:
    global _crypto_service
    if _crypto_service is None:
        master_key_hex = os.getenv("CRYPTO_KEY_HEX", "0" * 64)
        master_key = bytes.fromhex(master_key_hex)[:32]
        _crypto_service = SecureCryptoService(master_key)
    return _crypto_service


def get_claude_config_service(db: Session) -> ClaudeConfigService:
    global _claude_config_service
    if _claude_config_service is None:
        _claude_config_service = ClaudeConfigService(get_crypto_service(), db)
    return _claude_config_service


# ============ Claude Config Endpoints ============

@tutorials_router.post("/claude-configs", status_code=status.HTTP_201_CREATED)
async def save_claude_config(
    request: ClaudeConfigRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ClaudeConfigResponse:
    """Save or update Claude API configuration."""
    try:
        config_service = get_claude_config_service(db)
        config_dict = request.model_dump()
        config = config_service.save_config(str(current_user.id), config_dict)

        return ClaudeConfigResponse(
            id=str(config.id),
            user_id=str(config.user_id),
            base_url=config.base_url,
            model_name=config.model_name,
            system_prompt=config.system_prompt,
            is_default=config.is_default,
            created_at=config.created_at,
            last_used_at=config.last_used_at
        )
    except Exception as e:
        logger.error(f"Failed to save Claude config: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@tutorials_router.get("/claude-configs")
async def list_claude_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[ClaudeConfigResponse]:
    """List all Claude API configurations for current user."""
    try:
        config_service = get_claude_config_service(db)
        configs = config_service.get_user_configs(str(current_user.id))
        return [ClaudeConfigResponse(**c) for c in configs]
    except Exception as e:
        logger.error(f"Failed to list Claude configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@tutorials_router.get("/claude-configs/{config_id}")
async def get_claude_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Optional[ClaudeConfigResponse]:
    """Get a specific Claude API configuration."""
    try:
        config_service = get_claude_config_service(db)
        metadata = config_service.get_config_metadata(str(current_user.id), config_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Config not found")
        return ClaudeConfigResponse(**metadata)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get Claude config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@tutorials_router.delete("/claude-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_claude_config(
    config_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a Claude API configuration."""
    try:
        config_service = get_claude_config_service(db)
        if not config_service.delete_config(str(current_user.id), config_id):
            raise HTTPException(status_code=404, detail="Config not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete Claude config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Outline Generation Endpoints ============

@tutorials_router.post("/generate-outline", status_code=status.HTTP_202_ACCEPTED)
async def generate_outline(
    request: GenerateOutlineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> OutlineStatusResponse:
    """Generate a course outline synchronously for MVP."""
    try:
        # Validate config
        config_uuid = uuid.UUID(request.claude_config_id)
        config = db.query(ClaudeConfig).filter_by(
            id=config_uuid, user_id=current_user.id
        ).first()
        if not config:
            raise HTTPException(status_code=404, detail="Invalid Claude configuration")

        # Get or create knowledge mapping
        km_record = db.query(UserKnowledgeMapping).filter_by(user_id=current_user.id).first()
        mastery_map = km_record.mastery_map if km_record and km_record.mastery_map else {}

        # Create task log
        task_id = str(uuid.uuid4())
        task_log = TaskLog(
            user_id=str(current_user.id),
            task_type="generate_outline",
            status="running",
            progress=10,
            result_url=f"/api/v1/tutorials/outlines/{task_id}",
            created_at=datetime.utcnow()
        )
        db.add(task_log)
        db.commit()
        db.refresh(task_log)

        # Generate outline synchronously for MVP
        try:
            config_service = get_claude_config_service(db)
            profile = db.query(UserProfile).filter_by(user_id=current_user.id).first()
            profile_dict = profile.to_dict() if profile else {}

            generator = OutlineGenerator(db, get_crypto_service(), config_service)
            result = generator.generate(
                config_id=config_uuid,
                user_id=current_user.id,
                topics=request.topics,
                mastery_map=mastery_map
            )

            # Update task status
            task_log.status = "success"
            task_log.progress = 100
            task_log.details_json = result.get("outline", {})
            task_log.finished_at = datetime.utcnow()
            db.commit()

            # 检查大纲安全性
            outline_data = result.get("outline", {})
            security_scan = outline_data.get('_security_scan', {})

            if security_scan.get('needs_review'):
                task_log.details_json = {
                    **task_log.details_json,
                    'security_scan': security_scan,
                    'needs_review': True
                }
                db.commit()
                logger.warning(f"Outline flagged for review: {security_scan.get('reasons', [])}")

            return OutlineStatusResponse(
                task_id=task_id,
                status=OutlineStatus.COMPLETED,
                progress=100,
                result_url=f"/api/v1/tutorials/outlines/{task_id}",
                created_at=task_log.created_at,
                completed_at=task_log.finished_at,
                outline_data=result.get("outline")
            )

        except Exception as gen_error:
            task_log.status = "failed"
            task_log.error_message = str(gen_error)
            task_log.finished_at = datetime.utcnow()
            db.commit()

            return OutlineStatusResponse(
                task_id=task_id,
                status=OutlineStatus.FAILED,
                progress=0,
                error_message=str(gen_error),
                created_at=task_log.created_at
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit outline generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@tutorials_router.get("/outlines/{outline_id}")
async def get_outline_status(
    outline_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> OutlineStatusResponse:
    """Poll for outline generation status."""
    task_log = db.query(TaskLog).filter_by(
        id=outline_id,
        task_type="generate_outline",
        user_id=str(current_user.id)
    ).first()

    if not task_log:
        raise HTTPException(status_code=404, detail="Task not found")

    status_map = {
        'pending': OutlineStatus.PENDING,
        'running': OutlineStatus.IN_PROGRESS,
        'success': OutlineStatus.COMPLETED,
        'failed': OutlineStatus.FAILED
    }

    return OutlineStatusResponse(
        task_id=outline_id,
        status=status_map.get(task_log.status, OutlineStatus.PENDING),
        progress=task_log.progress or 0,
        result_url=task_log.result_url,
        error_message=task_log.error_message,
        created_at=task_log.created_at,
        completed_at=task_log.finished_at,
        outline_data=task_log.details_json if task_log.status == "success" else None
    )


@tutorials_router.put("/outlines/{outline_id}/confirm", status_code=status.HTTP_201_CREATED)
async def confirm_outline(
    outline_id: str,
    request: ConfirmOutlineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Confirm outline and create tutorial."""
    # Check task
    task_log = db.query(TaskLog).filter_by(
        id=outline_id, task_type="generate_outline", user_id=str(current_user.id)
    ).first()
    if not task_log or task_log.status != "success":
        raise HTTPException(status_code=400, detail="Outline not ready or failed")

    # Extract outline data
    outline_data = task_log.details_json or {}

    # Create tutorial
    tutorial = Tutorial(
        owner_id=str(current_user.id),
        title=request.title or outline_data.get("course_title", "New Personalized Tutorial"),
        description=request.description or outline_data.get("description", ""),
        outline=outline_data,
        status=TutorialStatus.DRAFT.value,
        total_chapters=outline_data.get("total_chapters", 8),
        current_chapter=1,
        created_at=datetime.utcnow()
    )
    db.add(tutorial)
    db.commit()
    db.refresh(tutorial)

    # Update task
    task_log.status = "success"
    task_log.details_json = {**task_log.details_json, "tutorial_id": str(tutorial.id)}
    db.commit()

    return {
        "tutorial_id": str(tutorial.id),
        "message": f"Tutorial '{tutorial.title}' created successfully",
        "tutorial": tutorial.to_dict(include_outline=True)
    }


# ============ Chapter Generation Endpoints ============

@tutorials_router.post("/{tutorial_id}/generate-next", status_code=status.HTTP_202_ACCEPTED)
async def generate_next_chapter(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generate the next chapter in a tutorial."""
    # Verify tutorial
    tutorial = db.query(Tutorial).filter_by(id=tutorial_id, owner_id=str(current_user.id)).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found or unauthorized")

    # Get next chapter number
    last_chapter = db.query(Chapter).filter_by(tutorial_id=tutorial_id).order_by(Chapter.chapter_number.desc()).first()
    next_number = (last_chapter.chapter_number + 1) if last_chapter else 1

    if next_number > (tutorial.total_chapters or 10):
        raise HTTPException(status_code=400, detail="All chapters generated")

    # Get Claude config
    config = db.query(ClaudeConfig).filter_by(user_id=str(current_user.id)).first()
    if not config:
        raise HTTPException(status_code=400, detail="No Claude configuration found")

    # Create task log
    task_id = str(uuid.uuid4())
    task_log = TaskLog(
        user_id=str(current_user.id),
        task_type="generate_chapter",
        status="running",
        progress=10,
        result_url=f"/api/v1/tutorials/{tutorial_id}/chapters/{next_number}",
        details_json={"tutorial_id": tutorial_id, "chapter_number": next_number},
        created_at=datetime.utcnow()
    )
    db.add(task_log)
    db.commit()
    db.refresh(task_log)

    # Generate chapter
    try:
        config_service = get_claude_config_service(db)
        profile = db.query(UserProfile).filter_by(user_id=str(current_user.id)).first()
        profile_dict = profile.to_dict() if profile else {}

        km_record = db.query(UserKnowledgeMapping).filter_by(user_id=str(current_user.id)).first()
        mastery_map = km_record.mastery_map if km_record and km_record.mastery_map else {}

        generator = ChapterGenerator(db, get_crypto_service(), config_service)
        result = generator.generate(
            config_id=config.id,
            user_id=current_user.id,
            tutorial_id=tutorial_id,
            chapter_number=next_number,
            outline_data=tutorial.outline or {},
            mastery_map=mastery_map
        )

        # Save chapter to database
        chapter_content = result.get("chapter_content", {})
        chapter = Chapter(
            id=str(uuid.uuid4()),
            tutorial_id=tutorial_id,
            chapter_number=next_number,
            title=chapter_content.get("chapter_title", f"Chapter {next_number}"),
            content=chapter_content,
            status="ready",
            prerequisite_check_passed=result.get("prerequisite_check_passed", True),
            generated_at=datetime.utcnow()
        )
        db.add(chapter)

        # 获取扫描结果（已在章节内容中）
        security_scan = chapter_content.get('_security_scan', {})

        # 如果内容需要审核，标记教程状态
        if security_scan.get('needs_review'):
            tutorial.status = TutorialStatus.REVIEWING.value
            logger.warning(f"Chapter {next_number} flagged for review: {security_scan.get('reasons', [])}")

        # Update tutorial
        tutorial.current_chapter = next_number + 1
        if next_number >= (tutorial.total_chapters or 10):
            tutorial.status = TutorialStatus.PUBLISHED.value

        db.commit()

        # Update task
        task_log.status = "success"
        task_log.progress = 100
        task_log.finished_at = datetime.utcnow()
        db.commit()

        return {
            "task_id": task_id,
            "chapter_number": next_number,
            "chapter_id": str(chapter.id),
            "status": "completed",
            "chapter": chapter.to_dict()
        }

    except Exception as e:
        task_log.status = "failed"
        task_log.error_message = str(e)
        task_log.finished_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=f"Chapter generation failed: {str(e)}")


@tutorials_router.get("/{tutorial_id}/chapters/{chapter_number}/status")
async def get_chapter_status(
    tutorial_id: str,
    chapter_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ChapterStatusResponse:
    """Check chapter generation status."""
    # Verify tutorial ownership
    tutorial = db.query(Tutorial).filter_by(id=tutorial_id, owner_id=str(current_user.id)).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    # Check if chapter exists
    chapter = db.query(Chapter).filter_by(
        tutorial_id=tutorial_id, chapter_number=chapter_number
    ).first()

    if chapter:
        return ChapterStatusResponse(
            tutorial_id=tutorial_id,
            chapter_number=chapter_number,
            status=ChapterStatus(chapter.status),
            progress=100,
            created_at=chapter.generated_at or datetime.utcnow(),
            completed_at=chapter.completed_at,
            chapter_content=chapter.content
        )

    # Check for pending task
    task_log = db.query(TaskLog).filter_by(
        user_id=str(current_user.id),
        task_type="generate_chapter"
    ).filter(
        TaskLog.details_json.contains(f'"chapter_number": {chapter_number}')
    ).order_by(TaskLog.created_at.desc()).first()

    if task_log:
        return ChapterStatusResponse(
            tutorial_id=tutorial_id,
            chapter_number=chapter_number,
            status=ChapterStatus.IN_PROGRESS if task_log.status == "running" else ChapterStatus.PENDING,
            progress=task_log.progress or 0,
            created_at=task_log.created_at
        )

    raise HTTPException(status_code=404, detail="Chapter not found")


@tutorials_router.get("/{tutorial_id}/chapters", response_model=Dict[str, Any])
async def list_chapters(
    tutorial_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List all chapters for a tutorial (summary only, no content)."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    chapters = db.query(Chapter).filter_by(tutorial_id=tutorial_id).order_by(Chapter.chapter_number).all()
    return {
        "data": [
            {
                "id": c.id,
                "chapter_number": c.chapter_number,
                "title": c.title,
                "status": c.status,
                "generated_at": c.generated_at.isoformat() if c.generated_at else None,
            }
            for c in chapters
        ],
        "total": len(chapters)
    }


@tutorials_router.get("/{tutorial_id}/chapters/{chapter_number}", response_model=Dict[str, Any])
async def get_chapter_content(
    tutorial_id: str,
    chapter_number: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get full chapter content including sections."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    chapter = Chapter.get_by_number(db=db, tutorial_id=tutorial_id, chapter_number=chapter_number)
    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_number} not found")

    return chapter.to_dict(include_content=True)


# ============ Tutorial CRUD Endpoints ============

@tutorials_router.get("/", response_model=Dict[str, Any])
async def list_tutorials(
    db: Session = Depends(get_db),
    public_only: bool = True,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """List tutorials."""
    query = db.query(Tutorial)
    if public_only:
        query = query.filter(Tutorial.is_public == True, Tutorial.status == TutorialStatus.PUBLISHED.value)

    offset = (page - 1) * limit
    tutorials = query.order_by(Tutorial.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()

    summaries = []
    for t in tutorials:
        summaries.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "owner_id": t.owner_id,
            "is_public": t.is_public,
            "status": t.status,
            "total_chapters": t.total_chapters,
            "current_chapter": t.current_chapter,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat()
        })

    return {
        "data": summaries,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@tutorials_router.get("/{tutorial_id}", response_model=TutorialDetail)
async def get_tutorial_detail(
    tutorial_id: str,
    db: Session = Depends(get_db)
) -> TutorialDetail:
    """Get tutorial details."""
    tutorial = db.query(Tutorial).filter_by(id=tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    chapters = db.query(Chapter).filter_by(tutorial_id=tutorial_id).order_by(Chapter.chapter_number).all()

    return TutorialDetail(
        id=tutorial.id,
        title=tutorial.title,
        description=tutorial.description,
        owner_id=tutorial.owner_id,
        is_public=tutorial.is_public,
        status=TutorialStatus(tutorial.status),
        total_chapters=tutorial.total_chapters,
        current_chapter=tutorial.current_chapter,
        created_at=tutorial.created_at,
        updated_at=tutorial.updated_at,
        outline=tutorial.outline,
        chapters=[
            ChapterSummary(
                id=c.id,
                tutorial_id=c.tutorial_id,
                chapter_number=c.chapter_number,
                title=c.title,
                status=ChapterStatus(c.status),
                generated_at=c.generated_at,
                completed_at=c.completed_at,
                estimated_reading_min=c.content.get("estimated_reading_min") if isinstance(c.content, dict) else None
            )
            for c in chapters
        ]
    )


@tutorials_router.put("/{tutorial_id}", response_model=TutorialSummary)
async def update_tutorial(
    tutorial_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> TutorialSummary:
    """Update a tutorial."""
    tutorial = db.query(Tutorial).filter_by(id=tutorial_id, owner_id=str(current_user.id)).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    for key, value in updates.items():
        if hasattr(tutorial, key) and key not in ['id', 'owner_id', 'created_at']:
            setattr(tutorial, key, value)

    db.commit()
    db.refresh(tutorial)
    return tutorial


@tutorials_router.delete("/{tutorial_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a tutorial."""
    tutorial = db.query(Tutorial).filter_by(id=tutorial_id, owner_id=str(current_user.id)).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    # Delete associated chapters
    db.query(Chapter).filter_by(tutorial_id=tutorial_id).delete()
    db.delete(tutorial)
    db.commit()
