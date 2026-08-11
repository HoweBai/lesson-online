"""User profile API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging

from ..database import get_db
from ..services.auth_service import get_current_user
from ..models.user import User
from ..models.profile import UserProfile
from ..models.task_log import TaskLog
from ..models.knowledge_mapping import UserKnowledgeMapping
from ..services.knowledge_inferencer import DynamicKnowledgeInferencer
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


class ProfileUpdateRequest(BaseModel):
    programming_level: Optional[int] = None
    math_background: Optional[str] = None
    learning_goal: Optional[str] = None
    available_hours_per_day: Optional[float] = None
    preferred_style: Optional[str] = None


class LearningProgress(BaseModel):
    total_tutorials: int = 0
    completed_chapters: int = 0
    in_progress_chapters: int = 0
    total_study_time_minutes: int = 0
    last_active: Optional[str] = None
    streak_days: int = 0


@router.get("/profile", response_model=Dict[str, Any])
async def get_user_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user's profile."""
    profile = db.query(UserProfile).filter_by(user_id=current_user.id).first()
    knowledge_map = db.query(UserKnowledgeMapping).filter_by(user_id=current_user.id).first()

    return {
        "user": current_user.to_dict(),
        "profile": profile.to_dict() if profile else {},
        "knowledge_mapping": knowledge_map.to_dict() if knowledge_map else {}
    }


@router.put("/profile", response_model=Dict[str, Any])
async def update_user_profile(
    updates: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update user profile."""
    profile = db.query(UserProfile).filter_by(user_id=current_user.id).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    # Update fields
    if updates.programming_level is not None:
        profile.programming_level = updates.programming_level
    if updates.math_background is not None:
        profile.math_background = updates.math_background
    if updates.learning_goal is not None:
        profile.learning_goal = updates.learning_goal
    if updates.available_hours_per_day is not None:
        profile.available_hours_per_day = updates.available_hours_per_day
    if updates.preferred_style is not None:
        profile.preferred_style = updates.preferred_style

    db.commit()
    db.refresh(profile)

    # Re-infer knowledge mapping
    inferencer = DynamicKnowledgeInferencer()
    mastery_map = inferencer.infer_knowledge_graph(profile.to_dict())

    km = db.query(UserKnowledgeMapping).filter_by(user_id=current_user.id).first()
    if km:
        km.mastery_map = mastery_map
        km.inferred_at = db.bind.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
    else:
        km = UserKnowledgeMapping(
            user_id=current_user.id,
            mastery_map=mastery_map
        )
        db.add(km)

    db.commit()

    return {
        "message": "Profile updated successfully",
        "profile": profile.to_dict(),
        "knowledge_mapping": km.to_dict()
    }


@router.get("/profile/progress", response_model=LearningProgress)
async def get_learning_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> LearningProgress:
    """Get user's learning progress statistics."""
    from ..models.tutorial import Tutorial
    from ..models.chapter import Chapter

    # Count tutorials
    total_tutorials = db.query(Tutorial).filter_by(owner_id=current_user.id).count()

    # Count completed chapters
    completed_chapters = db.query(Chapter).join(Tutorial).filter(
        Tutorial.owner_id == current_user.id,
        Chapter.status == "completed"
    ).count()

    # Count in-progress chapters
    in_progress_chapters = db.query(Chapter).join(Tutorial).filter(
        Tutorial.owner_id == current_user.id,
        Chapter.status == "in_progress"
    ).count()

    # Estimate study time (10 minutes per chapter on average)
    total_study_time = (completed_chapters + in_progress_chapters) * 10

    # Get last active time
    last_task = db.query(TaskLog).filter_by(user_id=current_user.id).order_by(
        TaskLog.created_at.desc()
    ).first()

    last_active = last_task.created_at.isoformat() if last_task else None

    # Calculate streak (simplified)
    streak_days = 0
    if last_task:
        from datetime import timedelta
        days_since_last = (db.bind.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0] -
                          last_task.created_at).days
        if days_since_last <= 1:
            streak_days = 7  # Assume 7 day streak for MVP

    return LearningProgress(
        total_tutorials=total_tutorials,
        completed_chapters=completed_chapters,
        in_progress_chapters=in_progress_chapters,
        total_study_time_minutes=total_study_time,
        last_active=last_active,
        streak_days=streak_days
    )


@router.get("/profile/stats")
async def get_learning_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed learning statistics."""
    from ..models.tutorial import Tutorial
    from ..models.chapter import Chapter
    from ..models.task_log import TaskLog
    from datetime import datetime, timedelta

    # Tutorial statistics
    tutorials = db.query(Tutorial).filter_by(owner_id=current_user.id).all()
    tutorial_stats = {
        "total": len(tutorials),
        "draft": sum(1 for t in tutorials if t.status == "draft"),
        "published": sum(1 for t in tutorials if t.status == "published"),
        "by_month": {}
    }

    for t in tutorials:
        month = t.created_at.strftime("%Y-%m") if t.created_at else "unknown"
        tutorial_stats["by_month"][month] = tutorial_stats["by_month"].get(month, 0) + 1

    # Chapter statistics
    chapters = db.query(Chapter).join(Tutorial).filter(
        Tutorial.owner_id == current_user.id
    ).all()

    chapter_stats = {
        "total": len(chapters),
        "completed": sum(1 for c in chapters if c.status == "completed"),
        "ready": sum(1 for c in chapters if c.status == "ready"),
        "in_progress": sum(1 for c in chapters if c.status == "in_progress"),
        "failed": sum(1 for c in chapters if c.status == "failed")
    }

    # Recent activity
    recent_tasks = db.query(TaskLog).filter_by(user_id=current_user.id).order_by(
        TaskLog.created_at.desc()
    ).limit(10).all()

    activity = [
        {
            "type": task.task_type,
            "status": task.status,
            "timestamp": task.created_at.isoformat()
        }
        for task in recent_tasks
    ]

    # Knowledge mapping
    km = db.query(UserKnowledgeMapping).filter_by(user_id=current_user.id).first()
    knowledge_stats = {}
    if km and km.mastery_map:
        knowledge_stats = {
            "topics": len(km.mastery_map),
            "beginner": sum(1 for v in km.mastery_map.values() if v == "beginner"),
            "intermediate": sum(1 for v in km.mastery_map.values() if v == "intermediate"),
            "advanced": sum(1 for v in km.mastery_map.values() if v == "advanced")
        }

    return {
        "tutorial_stats": tutorial_stats,
        "chapter_stats": chapter_stats,
        "knowledge_stats": knowledge_stats,
        "recent_activity": activity
    }


@router.post("/profile/infer-knowledge")
async def infer_knowledge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Manually trigger knowledge inference update."""
    profile = db.query(UserProfile).filter_by(user_id=current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    inferencer = DynamicKnowledgeInferencer()
    mastery_map = inferencer.infer_knowledge_graph(profile.to_dict())

    km = db.query(UserKnowledgeMapping).filter_by(user_id=current_user.id).first()
    if km:
        km.mastery_map = mastery_map
        km.inferred_at = db.bind.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]
    else:
        km = UserKnowledgeMapping(
            user_id=current_user.id,
            mastery_map=mastery_map
        )
        db.add(km)

    db.commit()

    return {
        "message": "Knowledge mapping updated",
        "mastery_map": km.mastery_map
    }
