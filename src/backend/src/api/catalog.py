"""Public catalog API endpoints for browsing shared tutorials."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging

from ..database import get_db
from ..models.tutorial import Tutorial
from ..models.public_catalog import PublicCatalog
from ..models.chapter import Chapter
from ..models.user import User
from ..services.auth_service import get_current_user
from ..schemas.api import TutorialStatus, ChapterStatus

logger = logging.getLogger(__name__)

catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


@catalog_router.get("/", response_model=Dict[str, Any])
async def list_public_tutorials(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = "publish_time",
    order: str = "desc"
) -> Dict[str, Any]:
    """List public tutorials with optional filtering and pagination."""
    query = db.query(PublicCatalog).join(Tutorial).filter(
        Tutorial.status == TutorialStatus.PUBLISHED.value
    )

    # Apply search filter
    if search:
        query = query.filter(
            Tutorial.title.ilike(f"%{search}%") |
            Tutorial.description.ilike(f"%{search}%")
        )

    # Apply sorting
    if sort_by == "views":
        sort_col = PublicCatalog.view_count
    elif sort_by == "likes":
        sort_col = PublicCatalog.like_count
    elif sort_by == "created_at":
        sort_col = Tutorial.created_at
    else:
        sort_col = PublicCatalog.publish_time

    if order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # Pagination
    total = query.count()
    offset = (page - 1) * limit
    catalogs = query.offset(offset).limit(limit).all()

    tutorials = []
    for catalog in catalogs:
        tutorial = catalog.tutorial
        chapters = db.query(Chapter).filter_by(tutorial_id=tutorial.id).order_by(Chapter.chapter_number).all()

        tutorials.append({
            "id": tutorial.id,
            "title": tutorial.title,
            "description": tutorial.description,
            "owner_id": tutorial.owner_id,
            "is_public": tutorial.is_public,
            "status": tutorial.status,
            "total_chapters": tutorial.total_chapters,
            "current_chapter": tutorial.current_chapter,
            "published_by": str(catalog.published_by),
            "publish_time": catalog.publish_time.isoformat() if catalog.publish_time else None,
            "view_count": catalog.view_count,
            "like_count": catalog.like_count,
            "chapter_count": len(chapters),
            "created_at": tutorial.created_at.isoformat(),
            "updated_at": tutorial.updated_at.isoformat()
        })

    return {
        "data": tutorials,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@catalog_router.get("/{tutorial_id}", response_model=Dict[str, Any])
async def get_public_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get details of a specific public tutorial."""
    catalog = db.query(PublicCatalog).join(Tutorial).filter(
        Tutorial.id == tutorial_id,
        Tutorial.status == TutorialStatus.PUBLISHED.value
    ).first()

    if not catalog:
        raise HTTPException(status_code=404, detail="Tutorial not found or not public")

    tutorial = catalog.tutorial
    chapters = db.query(Chapter).filter_by(tutorial_id=tutorial.id).order_by(Chapter.chapter_number).all()

    # Increment view count
    catalog.view_count += 1
    db.commit()

    return {
        "tutorial": {
            "id": tutorial.id,
            "title": tutorial.title,
            "description": tutorial.description,
            "owner_id": tutorial.owner_id,
            "is_public": tutorial.is_public,
            "status": tutorial.status,
            "total_chapters": tutorial.total_chapters,
            "current_chapter": tutorial.current_chapter,
            "created_at": tutorial.created_at.isoformat(),
            "updated_at": tutorial.updated_at.isoformat()
        },
        "chapters": [
            {
                "id": c.id,
                "chapter_number": c.chapter_number,
                "title": c.title,
                "status": c.status,
                "generated_at": c.generated_at.isoformat() if c.generated_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None
            }
            for c in chapters
        ],
        "view_count": catalog.view_count,
        "like_count": catalog.like_count,
        "publish_time": catalog.publish_time.isoformat() if catalog.publish_time else None
    }


@catalog_router.post("/{tutorial_id}/like", response_model=Dict[str, Any])
async def like_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Like a public tutorial."""
    catalog = db.query(PublicCatalog).filter_by(tutorial_id=tutorial_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    catalog.like_count += 1
    db.commit()

    return {"message": "Tutorial liked successfully", "like_count": catalog.like_count}


@catalog_router.post("/{tutorial_id}/report")
async def report_tutorial(
    tutorial_id: str,
    reason: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Report a tutorial as inappropriate."""
    catalog = db.query(PublicCatalog).filter_by(tutorial_id=tutorial_id).first()
    if not catalog:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    catalog.reported_count += 1
    db.commit()

    logger.info(f"Tutorial {tutorial_id} reported by user {user.id}: {reason}")
    return {"message": "Report submitted. Review team will assess."}


@catalog_router.get("/popular", response_model=List[Dict[str, Any]])
async def get_popular_tutorials(
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get the most popular tutorials."""
    tutorials = db.query(PublicCatalog).join(Tutorial).filter(
        Tutorial.status == TutorialStatus.PUBLISHED.value
    ).order_by(
        (PublicCatalog.like_count + PublicCatalog.view_count).desc()
    ).limit(10).all()

    result = []
    for catalog in tutorials:
        tutorial = catalog.tutorial
        result.append({
            "id": tutorial.id,
            "title": tutorial.title,
            "description": tutorial.description,
            "owner_id": tutorial.owner_id,
            "view_count": catalog.view_count,
            "like_count": catalog.like_count,
            "publish_time": catalog.publish_time.isoformat() if catalog.publish_time else None
        })

    return result
