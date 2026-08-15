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
from ..tasks.export_tasks import export_file_task
from fastapi.responses import PlainTextResponse, JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tutorials", tags=["export"])


@router.get("/{tutorial_id}/export/markdown")
async def export_markdown(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PlainTextResponse:
    """Export tutorial content as Markdown (synchronous)."""
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
    """Export tutorial content as JSON (synchronous)."""
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


@router.get("/{tutorial_id}/export/pdf")
async def export_pdf(
    tutorial_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Response:
    """Export tutorial content as PDF (synchronous)."""
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        (Tutorial.owner_id == current_user.id) | (Tutorial.is_public == True)
    ).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    try:
        export_service = create_export_service(db)
        result = export_service.export_to_pdf(tutorial_id)
        return Response(
            content=result["pdf_bytes"],
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={tutorial.title.replace(' ', '_')}.pdf"}
        )
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        logger.error(f"Export to PDF failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Async Export Endpoints ============

@router.post("/{tutorial_id}/export/{format_type}", status_code=status.HTTP_202_ACCEPTED)
async def export_file_async(
    tutorial_id: str,
    format_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Export tutorial content asynchronously with MinIO storage."""
    tutorial = db.query(Tutorial).filter(
        Tutorial.id == tutorial_id,
        (Tutorial.owner_id == current_user.id) | (Tutorial.is_public == True)
    ).first()
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    if format_type not in ("markdown", "json", "pdf"):
        raise HTTPException(status_code=400, detail=f"Invalid format: {format_type}")

    import uuid
    from ..models.task_log import TaskLog
    from datetime import datetime

    # Create task log
    task_id = str(uuid.uuid4())
    task_log = TaskLog(
        user_id=str(current_user.id),
        task_type=f"export_{format_type}",
        status="pending",
        progress=0,
        result_url=f"/api/v1/tutorials/{tutorial_id}/export/{format_type}/{task_id}",
        created_at=datetime.utcnow()
    )
    db.add(task_log)
    db.commit()
    db.refresh(task_log)

    # Submit async task
    export_file_task.delay(
        task_id=task_id,
        tutorial_id=tutorial_id,
        format_type=format_type,
        user_id=str(current_user.id),
        is_public=tutorial.is_public and tutorial.status == "published",
    )

    return {
        "task_id": task_id,
        "format": format_type,
        "status": "pending",
        "result_url": task_log.result_url,
    }


@router.get("/{tutorial_id}/export/{format_type}/{task_id}")
async def get_export_status(
    tutorial_id: str,
    format_type: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get export task status."""
    task_log = db.query(TaskLog).filter_by(
        id=task_id,
        user_id=str(current_user.id),
        task_type=f"export_{format_type}"
    ).first()

    if not task_log:
        raise HTTPException(status_code=404, detail="Export task not found")

    status_map = {
        "pending": "pending",
        "running": "running",
        "success": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
    }

    result = {
        "task_id": task_id,
        "status": status_map.get(task_log.status, "pending"),
        "progress": task_log.progress or 0,
        "created_at": task_log.created_at.isoformat(),
    }

    if task_log.status == "success" and task_log.details_json:
        result["download_url"] = task_log.details_json.get("download_url")
        result["size_bytes"] = task_log.details_json.get("size_bytes")
        result["completed_at"] = task_log.finished_at.isoformat() if task_log.finished_at else None

    if task_log.status == "failed" and task_log.error_message:
        result["error"] = task_log.error_message

    return result


@router.delete("/{tutorial_id}/export/{format_type}/{task_id}")
async def cancel_export(
    tutorial_id: str,
    format_type: str,
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel an export task."""
    task_log = db.query(TaskLog).filter_by(
        id=task_id,
        user_id=str(current_user.id),
        task_type=f"export_{format_type}"
    ).first()

    if not task_log:
        raise HTTPException(status_code=404, detail="Export task not found")

    if task_log.status in ("success", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Task already {task_log.status}")

    task_log.status = "cancelled"
    task_log.finished_at = datetime.utcnow()
    db.commit()

    return {"message": "Export task cancelled", "task_id": task_id}
