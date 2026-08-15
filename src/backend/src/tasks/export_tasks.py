"""Celery task for file export."""

import os
import uuid
from datetime import datetime
from typing import Dict, Any

from celery import shared_task
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..services.export_service import ExportService
from ..services.minio_service import MinioService
from ..models.task_log import TaskLog
from ..models.tutorial import Tutorial


@shared_task(bind=True, name='tasks.export.file')
def export_file_task(
    self,
    task_id: str,
    tutorial_id: str,
    format_type: str,
    user_id: str,
    is_public: bool = False,
) -> Dict[str, Any]:
    """Asynchronous file export task."""
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

        # Export file
        task_log.progress = 40
        db.commit()

        export_service = ExportService(db)
        if format_type == "markdown":
            result = export_service.export_to_markdown(tutorial_id)
            file_bytes = result["content"].encode('utf-8')
            extension = ".md"
            content_type = "text/markdown"
        elif format_type == "json":
            result = export_service.export_to_json(tutorial_id)
            import json as json_module
            file_bytes = json_module.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
            extension = ".json"
            content_type = "application/json"
        elif format_type == "pdf":
            result = export_service.export_to_pdf(tutorial_id)
            file_bytes = result["pdf_bytes"]
            extension = ".pdf"
            content_type = "application/pdf"
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

        # Check if cancelled during export
        if task_log.status == "cancelled":
            return {"status": "cancelled", "task_id": task_id}

        # Upload to MinIO
        task_log.progress = 70
        db.commit()

        minio_service = MinioService()
        filename = f"exports/{user_id}/{task_id}{extension}"
        if is_public:
            filename = f"public/{tutorial_id}/{task_id}{extension}"

        download_url = minio_service.upload_file(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
        )

        # Check if cancelled after upload
        if task_log.status == "cancelled":
            minio_service.delete_file(filename)
            return {"status": "cancelled", "task_id": task_id}

        # Update task log (progress 100%)
        task_log.status = "success"
        task_log.progress = 100
        task_log.details_json = {
            "download_url": download_url,
            "format": format_type,
            "size_bytes": len(file_bytes),
        }
        task_log.finished_at = datetime.utcnow()
        db.commit()

        return {
            "status": "success",
            "task_id": task_id,
            "download_url": download_url,
            "format": format_type,
            "size_bytes": len(file_bytes),
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
