"""Comment API endpoints for tutorial discussions."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from ..database import get_db
from ..models.user import User
from ..models.tutorial import Tutorial
from ..models.comment import Comment
from ..services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutorials", tags=["comments"])


class CreateCommentRequest(BaseModel):
    content: str
    parent_id: str = None


@router.post("/{tutorial_id}/comments", status_code=status.HTTP_201_CREATED, response_model=Dict[str, Any])
async def create_comment(
    tutorial_id: str,
    request: CreateCommentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a comment or reply on a tutorial."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    comment = Comment.create(
        db=db,
        user_id=str(current_user.id),
        tutorial_id=tutorial_id,
        content=request.content,
        parent_id=request.parent_id
    )
    return comment.to_dict()


@router.get("/{tutorial_id}/comments", response_model=Dict[str, Any])
async def get_comments(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get all comments for a tutorial."""
    tutorial = db.query(Tutorial).filter(Tutorial.id == tutorial_id).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    comments = Comment.get_by_tutorial(db=db, tutorial_id=tutorial_id)
    return {
        "data": [c.to_dict() for c in comments],
        "total": len(comments)
    }


router_comment = APIRouter(prefix="/comments", tags=["comments"])


@router_comment.post("/{comment_id}/like", response_model=Dict[str, Any])
async def like_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Like a comment."""
    try:
        count = Comment.like_comment(db=db, comment_id=comment_id)
        return {"like_count": count}
    except ValueError:
        raise HTTPException(status_code=404, detail="Comment not found")


@router_comment.delete("/{comment_id}", response_model=Dict[str, Any])
async def delete_comment(
    comment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Delete your own comment."""
    deleted = Comment.delete_comment(db=db, comment_id=comment_id, user_id=str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=403, detail="Cannot delete this comment")
    return {"success": True, "message": "Comment deleted"}
