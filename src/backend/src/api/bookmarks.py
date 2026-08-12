"""Bookmark API endpoints for tutorial favorites."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from ..database import get_db
from ..models.user import User
from ..models.tutorial import Tutorial
from ..models.bookmark import Bookmark
from ..services.auth_service import get_current_user

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


@router.post("/{tutorial_id}/bookmark", response_model=Dict[str, Any])
async def bookmark_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Bookmark (favorite) a tutorial."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    bookmark = Bookmark.create(db=db, user_id=str(current_user.id), tutorial_id=tutorial_id)
    if bookmark is None:
        return {
            "success": True,
            "message": "Already bookmarked",
            "bookmark_id": None
        }
    return {
        "success": True,
        "message": "Tutorial bookmarked",
        "bookmark_id": bookmark.id
    }


@router.delete("/{tutorial_id}/bookmark", response_model=Dict[str, Any])
async def unbookmark_tutorial(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Remove a bookmark from a tutorial."""
    deleted = Bookmark.delete(db=db, user_id=str(current_user.id), tutorial_id=tutorial_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return {"success": True, "message": "Bookmark removed"}


@router.get("/bookmarks", response_model=Dict[str, Any])
async def list_user_bookmarks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """Get all bookmarks for the current user."""
    result = Bookmark.get_by_user(db=db, user_id=str(current_user.id), page=page, limit=limit)
    return result
