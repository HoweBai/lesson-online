"""Tutorial export API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from ..database import get_db
from ..services.auth_service import get_current_user
from ..models.user import User
from ..models.tutorial import Tutorial
from ..services.export_service import ExportService, create_export_service
from fastapi.responses import PlainTextResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutorials", tags=["export"])


@router.get("/{tutorial_id}/export/markdown")
async def export_markdown(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PlainTextResponse:
    """Export tutorial content as Markdown."""
    # Verify ownership or public access
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        (Tutorial.owner_id == current_user.id) | (Tutorial.is_public == True)
    ).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    try:
        export_service = create_export_service(db)
        result = export_service.export_to_markdown(tutorial_id)
        return PlainTextResponse(content=result["content"])
    except Exception as e:
        logger.error(f"Export to markdown failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tutorial_id}/export/json")
async def export_json(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """Export tutorial content as JSON."""
    # Verify ownership or public access
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        (Tutorial.owner_id == current_user.id) | (Tutorial.is_public == True)
    ).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    try:
        export_service = create_export_service(db)
        result = export_service.export_to_json(tutorial_id)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Export to JSON failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tutorial_id}/export/outline")
async def export_outline(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """Export tutorial outline as JSON."""
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        (Tutorial.owner_id == current_user.id) | (Tutorial.is_public == True)
    ).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    outline = tutorial.outline or {}
    return JSONResponse(content={
        "tutorial_id": tutorial_id,
        "title": tutorial.title,
        "outline": outline
    })
